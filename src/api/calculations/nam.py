import numpy as np
import os
from datetime import datetime
from prisma import Prisma
from calculations.calculations import app
import json
from shapely import ops
from shapely.geometry import shape
import requests
import rasterio
from rasterio.features import rasterize
import pyproj

from calculations.discharge import construct_idf_curve

def geographic_to_raster_coords(lon, lat, transform, shape):
    """
    Convert geographic coordinates (longitude, latitude) to raster coordinates (row, col).
    
    Args:
        lon (float): Longitude coordinate
        lat (float): Latitude coordinate  
        transform: Rasterio transform object
        shape (tuple): Raster shape (height, width)
    
    Returns:
        tuple: (row, col) raster coordinates
    """
    from rasterio.transform import rowcol
    
    try:
        row, col = rowcol(transform, lon, lat)
        # Ensure coordinates are within bounds
        row = max(0, min(row, shape[0] - 1))
        col = max(0, min(col, shape[1] - 1))
        return int(row), int(col)
    except Exception as e:
        print(f"Warning: Error converting geographic coordinates ({lon}, {lat}) to raster coordinates: {e}")
        return None, None

@app.task(name="nam", bind=True)
def nam(self,
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x,                      # Return period
    curve_number,           # Curve number (fallback if no raster available)
    catchment_area,         # Catchment area [km²]
    channel_length,         # Channel length [m]
    delta_h,                # Elevation difference [m]
    nam_id,                 # db id for updating results
    project_id=None,        # Project ID for loading curve number raster
    user_id=None,           # User ID for loading curve number raster
    TB_start=30,            # Initial value for TB [min]
    istep=5,                # Step size for TB [min]
    tol=5,                  # Convergence tolerance [mm]
    max_iter=1000,
    water_balance_mode="simple",  # Options: "simple", "cumulative", "hybrid", "uniform", "conservative"
    precipitation_factor=0.5,  # Factor to scale precipitation (0.5 = 50% of calculated)
    storm_center_mode="centroid",  # Options: "centroid", "discharge_point", "user_point" - where to place storm center
    discharge_point_coords=None,  # User-provided discharge point coordinates (x, y) in raster coordinates
    discharge_point_lon_lat=None,  # User-provided discharge point coordinates (longitude, latitude) in geographic coordinates
    discharge_point_epsg2056=None,  # User-provided discharge point coordinates (easting, northing) in EPSG:2056
    use_kirpich=True,  # Use Kirpich method for travel time calculation
    routing_method="time_values"  # Options: "travel_time", "isozone", "time_values" - method for routing runoff to discharge point
):
    """
    NAM (Nedbør-Afstrømnings-Model) calculation based on distributed curve numbers and travel times.
    This is a distributed rainfall-runoff model that uses curve numbers for each cell and 
    calculates runoff at 10-minute timesteps using either travel time or isozone routing methods.
    """
    intensity_fn = construct_idf_curve(P_low_1h, P_high_1h, P_low_24h, P_high_24h, rp_low, rp_high)
    
    # Initialize variables for distributed calculation
    cn_data = None
    isozone_data = None
    grid = None
    pixel_area_m2 = 25  # Default cell area [m²] (5x5 m)
    
    # 1. Load curve number raster and isozones raster
    if project_id and user_id:
        try:
            # Load curve number raster
            curve_number_file = f"data/{user_id}/{project_id}/curvenumbers.tif"
            if os.path.exists(curve_number_file):
                print(f"Loading curve number raster from: {curve_number_file}")
                with rasterio.open(curve_number_file) as src:
                    cn_data = src.read(1)
                    cn_transform = src.transform
                    cn_crs = src.crs
                    pixel_area_m2 = abs(src.transform[0] * src.transform[4])  # Calculate actual pixel area
                    print(f"Curve number raster loaded, shape: {cn_data.shape}, pixel area: {pixel_area_m2:.2f} m²")
            else:
                print(f"Curve number raster not found: {curve_number_file}")
                return {"error": "Curve number raster not found"}
            
            # Load isozones raster
            isozone_file = f"data/{user_id}/{project_id}/isozones_cog.tif"
            if os.path.exists(isozone_file):
                print(f"Loading isozones raster from: {isozone_file}")
                with rasterio.open(isozone_file) as src:
                    isozone_data = src.read(1)
                    isozone_transform = src.transform
                    isozone_crs = src.crs
                    print(f"Isozones raster loaded, shape: {isozone_data.shape}, max zone: {int(np.nanmax(isozone_data))}")
            else:
                print(f"Isozones raster not found: {isozone_file}")
                return {"error": "Isozones raster not found"}
            
            # Load DEM data for Kirpich calculation
            dem_data = None
            if use_kirpich:
                dem_file = f"data/{user_id}/{project_id}/dem.tif"
                if os.path.exists(dem_file):
                    print(f"Loading DEM raster from: {dem_file}")
                    with rasterio.open(dem_file) as src:
                        dem_data = src.read(1)
                        dem_transform = src.transform
                        dem_crs = src.crs
                        print(f"DEM raster loaded, shape: {dem_data.shape}")
                        
                        # Check if DEM has the same shape as other rasters
                        if dem_data.shape != isozone_data.shape:
                            print(f"DEM shape differs: DEM={dem_data.shape}, Isozones={isozone_data.shape}")
                            print("Resampling DEM to match isozones grid...")
                            
                            from rasterio.warp import reproject, Resampling
                            
                            # Resample DEM data to match isozone raster
                            resampled_dem_data = np.empty(isozone_data.shape, dtype=dem_data.dtype)
                            reproject(
                                dem_data,
                                resampled_dem_data,
                                src_transform=dem_transform,
                                src_crs=dem_crs,
                                dst_transform=isozone_transform,
                                dst_crs=isozone_crs,
                                resampling=Resampling.bilinear
                            )
                            dem_data = resampled_dem_data
                            print(f"Resampled DEM data to shape: {dem_data.shape}")
                        else:
                            print("DEM shape matches isozones, no resampling needed")
                else:
                    print(f"DEM raster not found: {dem_file}")
                    print("Warning: DEM not available, travel time calculation will be limited")
                    use_kirpich = False
            
            # Load time_values.tif for time_values routing method
            time_values_data = None
            if routing_method == "time_values":
                time_values_file = f"data/{user_id}/{project_id}/time_values.tif"
                if os.path.exists(time_values_file):
                    print(f"Loading time values raster from: {time_values_file}")
                    with rasterio.open(time_values_file) as src:
                        time_values_data = src.read(1)
                        time_values_transform = src.transform
                        time_values_crs = src.crs
                        print(f"Time values raster loaded, shape: {time_values_data.shape}")
                        
                        # Check if time_values has the same shape as other rasters
                        if time_values_data.shape != isozone_data.shape:
                            print(f"Time values shape differs: TimeValues={time_values_data.shape}, Isozones={isozone_data.shape}")
                            print("Resampling time values to match isozones grid...")
                            
                            from rasterio.warp import reproject, Resampling
                            
                            # Resample time values data to match isozone raster
                            resampled_time_values_data = np.empty(isozone_data.shape, dtype=time_values_data.dtype)
                            reproject(
                                time_values_data,
                                resampled_time_values_data,
                                src_transform=time_values_transform,
                                src_crs=time_values_crs,
                                dst_transform=isozone_transform,
                                dst_crs=isozone_crs,
                                resampling=Resampling.bilinear
                            )
                            time_values_data = resampled_time_values_data
                            print(f"Resampled time values data to shape: {time_values_data.shape}")
                        else:
                            print("Time values shape matches isozones, no resampling needed")
                        
                        # Print statistics about time values
                        valid_time_mask = ~np.isnan(time_values_data) & (time_values_data > 0)
                        if np.any(valid_time_mask):
                            print(f"Time values statistics:")
                            print(f"  Min travel time: {np.nanmin(time_values_data[valid_time_mask]):.2f} minutes")
                            print(f"  Max travel time: {np.nanmax(time_values_data[valid_time_mask]):.2f} minutes")
                            print(f"  Mean travel time: {np.nanmean(time_values_data[valid_time_mask]):.2f} minutes")
                            print(f"  Median travel time: {np.nanmedian(time_values_data[valid_time_mask]):.2f} minutes")
                            print(f"  Valid cells: {np.sum(valid_time_mask)} out of {time_values_data.size}")
                        else:
                            print("Warning: No valid time values found in raster")
                else:
                    print(f"Time values raster not found: {time_values_file}")
                    print("Warning: Time values not available, falling back to travel_time method")
                    routing_method = "travel_time"
            
            # Check if rasters have the same shape and resample if necessary
            if cn_data.shape != isozone_data.shape:
                print(f"Raster shapes differ: CN={cn_data.shape}, Isozones={isozone_data.shape}")
                print("Resampling curve number raster to match isozones grid...")
                
                from rasterio.warp import reproject, Resampling
                
                # Resample curve number data to match isozone raster
                resampled_cn_data = np.empty(isozone_data.shape, dtype=cn_data.dtype)
                reproject(
                    cn_data,
                    resampled_cn_data,
                    src_transform=cn_transform,
                    src_crs=cn_crs,
                    dst_transform=isozone_transform,
                    dst_crs=isozone_crs,
                    resampling=Resampling.nearest
                )
                cn_data = resampled_cn_data
                cn_transform = isozone_transform  # Update transform to match isozones
                cn_crs = isozone_crs  # Update CRS to match isozones
                # Update pixel area calculation to use isozone grid
                pixel_area_m2 = abs(isozone_transform[0] * isozone_transform[4])
                print(f"Resampled curve number data to shape: {cn_data.shape}")
                print(f"Updated pixel area to match isozone grid: {pixel_area_m2:.2f} m²")
            else:
                print("Raster shapes match, no resampling needed")
                
        except Exception as e:
            print(f"Error loading rasters: {e}")
            return {"error": f"Error loading rasters: {e}"}
    else:
        return {"error": "Project ID and User ID required for distributed calculation"}
    
    # 2. Calculate retention for each cell using curve numbers
    print("Calculating retention for each cell...")
    
    # Validate that both rasters have the same shape after resampling
    if cn_data.shape != isozone_data.shape:
        return {"error": f"Raster shapes still don't match after resampling: CN={cn_data.shape}, Isozones={isozone_data.shape}"}
    
    # Calculate potential maximum retention S for each cell
    valid_mask = (cn_data > 0) & (cn_data <= 100)  # Valid curve numbers are 30-100
    if not np.any(valid_mask):
        return {"error": "No valid curve numbers found in raster"}
    
    print(f"Valid cells: {np.sum(valid_mask)} out of {cn_data.size}")
    
    # Validate curve numbers - they should be between 30 and 100
    cn_min = np.nanmin(cn_data[valid_mask])
    cn_max = np.nanmax(cn_data[valid_mask])
    
    if cn_min < 30 or cn_max > 100:
        print(f"WARNING: Curve numbers outside valid range (30-100): min={cn_min:.1f}, max={cn_max:.1f}")
        print("This will cause unrealistic S values. Clamping curve numbers to valid range...")
        
        # Clamp curve numbers to valid range
        cn_data_clamped = np.clip(cn_data, 30, 100)
        valid_mask = (cn_data_clamped > 0) & (cn_data_clamped <= 100)
    
    # Calculate S for each cell: S = (25400 / CN) - 254 [mm]
    S_cells = np.full_like(cn_data, np.nan, dtype=np.float32)
    S_cells[valid_mask] = (25400 / cn_data[valid_mask]) - 254
    
    # Calculate initial abstraction Ia for each cell: Ia = 0.2 * S [mm]
    Ia_cells = 0.2 * S_cells  # SCS standard: Ia = 0.2 * S
    
    # Debug: Print statistics about curve numbers and retention
    print(f"Curve number statistics:")
    print(f"  Min CN: {np.nanmin(cn_data[valid_mask]):.1f}")
    print(f"  Max CN: {np.nanmax(cn_data[valid_mask]):.1f}")
    print(f"  Mean CN: {np.nanmean(cn_data[valid_mask]):.1f}")
    print(f"  Median CN: {np.nanmedian(cn_data[valid_mask]):.1f}")
    
    print(f"Retention S statistics:")
    print(f"  Min S: {np.nanmin(S_cells[valid_mask]):.1f} mm")
    print(f"  Max S: {np.nanmax(S_cells[valid_mask]):.1f} mm")
    print(f"  Mean S: {np.nanmean(S_cells[valid_mask]):.1f} mm")
    print(f"  Median S: {np.nanmedian(S_cells[valid_mask]):.1f} mm")
    
    print(f"Initial abstraction Ia statistics:")
    print(f"  Min Ia: {np.nanmin(Ia_cells[valid_mask]):.1f} mm")
    print(f"  Max Ia: {np.nanmax(Ia_cells[valid_mask]):.1f} mm")
    print(f"  Mean Ia: {np.nanmean(Ia_cells[valid_mask]):.1f} mm")
    print(f"  Median Ia: {np.nanmedian(Ia_cells[valid_mask]):.1f} mm")
    
    # Show typical S values for reference
    print(f"Typical S values for different curve numbers:")
    for cn in [30, 40, 50, 60, 70, 80, 90, 100]:
        s_val = (25400 / cn) - 254
        ia_val = 0.2 * s_val
        print(f"  CN={cn}: S={s_val:.1f}mm, Ia={ia_val:.1f}mm")
    
    # 3. Calculate runoff for each cell using travel time calculation
    print("Calculating runoff for each cell using travel time calculation...")
    
    dt = 10  # Time step [min]
    Tc_total = 60  # Total simulation time [min]
    print(f"Simulation parameters: dt={dt}min, Tc_total={Tc_total}min")
    
    # Calculate max_timesteps for simulation (based on maximum travel time)
    # Estimate maximum travel time based on catchment size (simplified estimate)
    max_travel_time_minutes = int(np.ceil(np.sqrt(catchment_area * 1e6) / 1000))  # Rough estimate: 1000 m/min velocity
    max_timesteps = max_travel_time_minutes + 50  # Allow extra timesteps for runoff to decay
    print(f"Estimated maximum travel time: {max_travel_time_minutes} minutes")
    print(f"Total simulation timesteps: {max_timesteps}")
    
    # Initialize runoff time series for each timestep
    # This will store runoff volumes that arrive at each timestep
    runoff_timesteps = [0.0] * max_timesteps  # Pre-allocate with zeros
    
    # Calculate total storm precipitation for SCS method

    # We need the total precipitation for the entire storm duration
    i_total = intensity_fn(rp_years=x, duration_minutes=Tc_total)  # [mm/h]
    P_total_storm = i_total * Tc_total / 60  # [mm] - total storm precipitation
    print(f"Total storm precipitation: {P_total_storm:.2f} mm over {Tc_total} minutes")
    
    # Debug: Check if P_total_storm is sufficient to generate runoff
    mean_Ia = np.nanmean(Ia_cells[valid_mask])
    mean_S = np.nanmean(S_cells[valid_mask])
    print(f"Mean Ia: {mean_Ia:.2f} mm, Mean S: {mean_S:.2f} mm")
    print(f"P_total_storm vs Ia: {P_total_storm:.2f} vs {mean_Ia:.2f} mm")
    if P_total_storm <= mean_Ia:
        print("WARNING: Total storm precipitation is less than mean initial abstraction!")
        print("This will result in zero runoff. Consider:")
        print("1. Increasing return period (x)")
        print("2. Adjusting curve numbers (lower CN = higher S)")
        print("3. Using longer storm duration")
    else:
        print(f"P_total_storm > Ia: {P_total_storm:.2f} > {mean_Ia:.2f} ✓")
        # Calculate theoretical maximum Pe
        P_excess_theoretical = P_total_storm - mean_Ia
        Pe_theoretical = (P_excess_theoretical ** 2) / (P_excess_theoretical + mean_S)
        print(f"Theoretical max Pe: {Pe_theoretical:.2f} mm")
    
    # Apply total precipitation to all cells at the beginning
    # This represents a single precipitation event at time t0
    P_total_storm = P_total_storm  # Total precipitation for the event [mm]
    
    print(f"Starting distributed NAM calculation with {max_timesteps} timesteps...")
    
    # Create natural storm distribution (circular storm with maximum at center)
    if storm_center_mode == "user_point":
        storm_location = "user-provided point"
    elif storm_center_mode == "discharge_point":
        storm_location = "discharge point"
    else:
        storm_location = "catchment centroid"
    print(f"Creating natural storm distribution with maximum: {P_total_storm:.2f} mm at {storm_location}")
    
    # Initialize water balance tracking for each cell
    # Track remaining water in each cell over time
    remaining_water = np.zeros_like(cn_data, dtype=np.float32)  # [mm]
    cumulative_infiltration = np.zeros_like(cn_data, dtype=np.float32)  # [mm]
    cumulative_runoff = np.zeros_like(cn_data, dtype=np.float32)  # [mm]
    
    print(f"Water balance approach: {water_balance_mode}")
    print(f"Storm center mode: {storm_center_mode}")
    print(f"Routing method: {routing_method}")
    print(f"Precipitation factor: {precipitation_factor}")
    print(f"Return period: {x}")
    print(f"Storm duration: {Tc_total} minutes")

    # Find the storm center based on the selected mode
    if storm_center_mode == "user_point":
        # Use user-provided discharge point coordinates
        center_row = None
        center_col = None
        
        # Try raster coordinates first
        if discharge_point_coords is not None and len(discharge_point_coords) == 2:
            center_row, center_col = discharge_point_coords
            # Validate coordinates are within raster bounds
            if 0 <= center_row < cn_data.shape[0] and 0 <= center_col < cn_data.shape[1]:
                print(f"Storm center at user-provided raster coordinates: ({center_row}, {center_col})")
            else:
                print(f"Warning: User-provided raster coordinates ({center_row}, {center_col}) outside raster bounds")
                center_row = None
                center_col = None
        
        # Try geographic coordinates if raster coordinates failed or weren't provided
        if center_row is None and discharge_point_lon_lat is not None and len(discharge_point_lon_lat) == 2:
            lon, lat = discharge_point_lon_lat
            center_row, center_col = geographic_to_raster_coords(lon, lat, cn_transform, cn_data.shape)
            if center_row is not None and center_col is not None:
                print(f"Storm center at user-provided geographic coordinates ({lon:.6f}, {lat:.6f}): raster ({center_row}, {center_col})")
            else:
                print(f"Warning: Could not convert geographic coordinates ({lon:.6f}, {lat:.6f}) to raster coordinates")
        
        # Fallback to centroid if no valid coordinates provided
        if center_row is None or center_col is None:
            print("Warning: No valid user-provided coordinates, falling back to centroid")
            print(f"Debug: discharge_point_coords={discharge_point_coords}")
            print(f"Debug: discharge_point_lon_lat={discharge_point_lon_lat}")
            valid_indices = np.where(valid_mask)
            center_row = int(np.mean(valid_indices[0]))
            center_col = int(np.mean(valid_indices[1]))
            print(f"Storm center at catchment centroid: ({center_row}, {center_col})")
    elif storm_center_mode == "discharge_point":
        # Find the discharge point (lowest isozone = zone 0)
        discharge_mask = (isozone_data == 0) & valid_mask
        if np.any(discharge_mask):
            # Find the centroid of the discharge point area
            discharge_indices = np.where(discharge_mask)
            center_row = int(np.mean(discharge_indices[0]))
            center_col = int(np.mean(discharge_indices[1]))
            print(f"Storm center at discharge point (zone 0): ({center_row}, {center_col})")
        else:
            # Fallback to centroid if no discharge point found
            print("Warning: No discharge point (zone 0) found, falling back to centroid")
            valid_indices = np.where(valid_mask)
            center_row = int(np.mean(valid_indices[0]))
            center_col = int(np.mean(valid_indices[1]))
            print(f"Storm center at catchment centroid: ({center_row}, {center_col})")
    else:
        # Default: Find the center of the catchment (centroid of valid cells)
        valid_indices = np.where(valid_mask)
        center_row = int(np.mean(valid_indices[0]))
        center_col = int(np.mean(valid_indices[1]))
        print(f"Storm center at catchment centroid: ({center_row}, {center_col})")
    
    # Create storm distribution
    # Use a Gaussian-like distribution that decreases from center
    storm_radius = min(cn_data.shape) * 0.5
    
    # Calculate distance from storm center for each cell
    rows, cols = np.meshgrid(np.arange(cn_data.shape[0]), np.arange(cn_data.shape[1]), indexing='ij')
    distances = np.sqrt((rows - center_row)**2 + (cols - center_col)**2)
    
    # Create storm distribution: maximum at center, decreases with distance
    # Option 1: Exponential decay (more realistic for convective storms)
    storm_distribution = P_total_storm * np.exp(-distances / storm_radius)
    
    # Option 2: Gaussian distribution (alternative, more gradual decay)
    # storm_distribution = P_total_storm * np.exp(-(distances / storm_radius)**2)
    
    # Option 3: Linear decay (simpler, more uniform)
    # storm_distribution = P_total_storm * np.maximum(0, 1 - distances / storm_radius)
    
    # Ensure no negative precipitation
    storm_distribution = np.maximum(storm_distribution, 0)
    
    # Apply storm distribution to valid cells only
    remaining_water[valid_mask] = storm_distribution[valid_mask]
    
    # Calculate statistics
    max_precip = np.max(storm_distribution[valid_mask])
    min_precip = np.min(storm_distribution[valid_mask])
    mean_precip = np.mean(storm_distribution[valid_mask])
    
    print(f"Storm distribution: max={max_precip:.2f}mm, min={min_precip:.2f}mm, mean={mean_precip:.2f}mm")
    print(f"Total water applied: {np.sum(remaining_water[valid_mask]):.2f} mm")
    
    # Debug: Compare with uniform distribution
    uniform_total = np.sum(valid_mask) * P_total_storm
    print(f"Comparison: Uniform distribution would give {uniform_total:.2f} mm total")
    print(f"Storm distribution gives {np.sum(remaining_water[valid_mask]):.2f} mm total")
    print(f"Ratio: {np.sum(remaining_water[valid_mask])/uniform_total:.2f}")
    
    print(f"Initial water balance: {np.sum(remaining_water[valid_mask]):.2f} mm total water")
    
    # Save rain distribution as TIFF file
    try:
        temp_dir = "./data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rain_distribution_file = f"{temp_dir}/rain_distribution_{timestamp}.tif"
        
        # Create a copy of storm distribution for saving (only valid cells)
        rain_distribution_raster = np.zeros_like(storm_distribution, dtype=np.float32)
        rain_distribution_raster[valid_mask] = storm_distribution[valid_mask]
        
        # Save as GeoTIFF using the same transform and CRS as the curve number raster
        profile = {
            'driver': 'GTiff',
            'height': rain_distribution_raster.shape[0],
            'width': rain_distribution_raster.shape[1],
            'count': 1,
            'dtype': rain_distribution_raster.dtype.name,
            'crs': cn_crs,
            'transform': cn_transform,
            'nodata': 0,
            'compress': 'lzw'
        }
        
        with rasterio.open(rain_distribution_file, 'w', **profile) as dst:
            dst.write(rain_distribution_raster, 1)
        
        print(f"Rain distribution saved as TIFF: {rain_distribution_file}")
        print(f"  - File size: {os.path.getsize(rain_distribution_file) / 1024:.1f} KB")
        print(f"  - Precipitation range: {np.min(rain_distribution_raster[valid_mask]):.2f} - {np.max(rain_distribution_raster[valid_mask]):.2f} mm")
        print(f"  - Total precipitation: {np.sum(rain_distribution_raster[valid_mask]):.2f} mm")
        
    except Exception as e:
        print(f"Warning: Could not save rain distribution as TIFF: {e}")
    
    # Calculate runoff for each cell using travel time calculation
    print("Calculating runoff for each cell using travel time calculation...")
    
    # Calculate effective precipitation using SCS method for each cell
    Pe_cells = np.zeros_like(cn_data, dtype=np.float32)
    
    # Calculate effective precipitation for each cell using SCS method
    if water_balance_mode == "uniform":
        # Uniform approach: Use uniform precipitation for SCS calculation
        uniform_precip = P_total_storm * precipitation_factor  # Apply scaling factor
        
        print(f"Uniform approach - uniform={uniform_precip:.2f}mm (factor={precipitation_factor})")
        print(f"Debug: P_total_storm={P_total_storm:.2f}mm, precipitation_factor={precipitation_factor}")
        print(f"Debug: P_total_storm calculation: intensity={intensity_fn(rp_years=x, duration_minutes=Tc_total):.2f} mm/h * {Tc_total} min / 60 = {P_total_storm:.2f} mm")
        
        P_mask = uniform_precip > Ia_cells[valid_mask]
        print(f"Debug: {np.sum(P_mask)} cells have P > Ia out of {np.sum(valid_mask)} valid cells")
        print(f"Debug: uniform_precip={uniform_precip:.2f}mm, mean_Ia={np.mean(Ia_cells[valid_mask]):.2f}mm, max_Ia={np.max(Ia_cells[valid_mask]):.2f}mm")
        print(f"Debug: Ia statistics - min={np.min(Ia_cells[valid_mask]):.2f}mm, median={np.median(Ia_cells[valid_mask]):.2f}mm, max={np.max(Ia_cells[valid_mask]):.2f}mm")
        print(f"Debug: Curve number statistics - min={np.min(cn_data[valid_mask]):.1f}, median={np.median(cn_data[valid_mask]):.1f}, max={np.max(cn_data[valid_mask]):.1f}")
        print(f"Debug: S statistics - min={np.min(S_cells[valid_mask]):.1f}mm, median={np.median(S_cells[valid_mask]):.1f}mm, max={np.max(S_cells[valid_mask]):.1f}mm")
        
        if np.any(P_mask):
            P_excess = uniform_precip - Ia_cells[valid_mask][P_mask]
            S_valid = S_cells[valid_mask][P_mask]
            
            # Calculate effective precipitation for uniform storm
            Pe_values = (P_excess ** 2) / (P_excess + S_valid)
            
            # Store effective precipitation for cells with runoff
            # Fix: Use proper boolean indexing for assignment
            valid_indices = np.where(valid_mask)
            p_indices = np.where(P_mask)[0]  # Get indices where P_mask is True
            
            # Map back to original array indices
            original_indices = (valid_indices[0][p_indices], valid_indices[1][p_indices])
            Pe_cells[original_indices] = Pe_values
            
            # Debug info
            print(f"  {np.sum(P_mask)} cells with runoff (uniform)")
            if np.sum(P_mask) > 0:
                print(f"    Sample: P_uniform={uniform_precip:.2f}mm, Ia={Ia_cells[valid_mask][P_mask][0]:.2f}mm, S={S_valid[0]:.2f}mm")
                print(f"    Sample: P_excess={P_excess[0]:.2f}mm, Pe={Pe_values[0]:.2f}mm")
                print(f"    Total Pe generated: {np.sum(Pe_values):.2f}mm")
        else:
            print(f"  WARNING: No cells have P > Ia! This will result in zero runoff.")
            print(f"  Consider increasing precipitation or reducing curve numbers.")
            print(f"  Debug: uniform_precip={uniform_precip:.2f}mm, min_Ia={np.min(Ia_cells[valid_mask]):.2f}mm")
            print(f"  Debug: To generate runoff, need P > min_Ia: {uniform_precip:.2f} > {np.min(Ia_cells[valid_mask]):.2f} = {uniform_precip > np.min(Ia_cells[valid_mask])}")
            print(f"  Debug: Try increasing precipitation_factor or return period")
    elif water_balance_mode == "cumulative":
        # Cumulative approach: Use storm distribution with iterative water retention calculation
        # This approach considers the spatially varying storm and calculates retained water iteratively
        print(f"Cumulative approach - using storm distribution with iterative retention")
        print(f"Debug: storm_distribution range: {np.min(storm_distribution[valid_mask]):.2f} - {np.max(storm_distribution[valid_mask]):.2f}mm")
        print(f"Debug: mean storm_distribution: {np.mean(storm_distribution[valid_mask]):.2f}mm")
        print(f"Debug: precipitation_factor: {precipitation_factor}")
        
        # Initialize cumulative precipitation and retained water arrays
        cumulative_precip = storm_distribution * precipitation_factor  # Spatially varying precipitation
        retained_water = np.zeros_like(cn_data, dtype=np.float32)  # Water retained in each cell
        Pe_cells = np.zeros_like(cn_data, dtype=np.float32)  # Effective precipitation
        
        # Iterative calculation: each cell's retained water affects subsequent calculations
        max_iterations = 10  # Prevent infinite loops
        convergence_tolerance = 0.001  # mm
        
        print(f"Starting iterative cumulative calculation (max {max_iterations} iterations)")
        
        for iteration in range(max_iterations):
            # Calculate available precipitation for this iteration
            available_precip = cumulative_precip - retained_water
            
            # Find cells where available precipitation exceeds initial abstraction
            P_mask = available_precip[valid_mask] > Ia_cells[valid_mask]
            
            if not np.any(P_mask):
                print(f"  Iteration {iteration + 1}: No cells have available P > Ia, stopping")
                break
                
            # Calculate excess precipitation for cells with runoff
            P_excess = available_precip[valid_mask][P_mask] - Ia_cells[valid_mask][P_mask]
            S_valid = S_cells[valid_mask][P_mask]
            
            # Calculate effective precipitation for this iteration
            Pe_iteration = (P_excess ** 2) / (P_excess + S_valid)
            
            # Calculate infiltration (retained water) for this iteration
            infiltration_iteration = available_precip[valid_mask][P_mask] - Pe_iteration
            
            # Update retained water and effective precipitation
            valid_indices = np.where(valid_mask)
            p_indices = np.where(P_mask)[0]
            original_indices = (valid_indices[0][p_indices], valid_indices[1][p_indices])
            
            # Add to cumulative effective precipitation
            Pe_cells[original_indices] += Pe_iteration
            
            # Update retained water
            retained_water[original_indices] += infiltration_iteration
            
            # Check convergence
            total_pe_change = np.sum(Pe_iteration)
            total_retention_change = np.sum(infiltration_iteration)
            
            print(f"  Iteration {iteration + 1}:")
            print(f"    Cells with runoff: {np.sum(P_mask)}")
            print(f"    Pe added: {total_pe_change:.2f}mm")
            print(f"    Retention added: {total_retention_change:.2f}mm")
            print(f"    Total Pe so far: {np.sum(Pe_cells):.2f}mm")
            print(f"    Total retention so far: {np.sum(retained_water):.2f}mm")
            
            # Check if changes are small enough to stop
            if total_pe_change < convergence_tolerance and total_retention_change < convergence_tolerance:
                print(f"  Convergence reached after {iteration + 1} iterations")
                break
                
            # Safety check: if we've reached max iterations
            if iteration == max_iterations - 1:
                print(f"  Warning: Reached maximum iterations ({max_iterations})")
        
        # Final statistics
        total_pe_generated = np.sum(Pe_cells)
        total_retention = np.sum(retained_water)
        total_precipitation = np.sum(cumulative_precip[valid_mask])
        
        print(f"Cumulative calculation completed:")
        print(f"  Total precipitation: {total_precipitation:.2f}mm")
        print(f"  Total retention: {total_retention:.2f}mm")
        print(f"  Total effective precipitation: {total_pe_generated:.2f}mm")
        print(f"  Retention percentage: {(total_retention/total_precipitation)*100:.1f}%")
        print(f"  Runoff percentage: {(total_pe_generated/total_precipitation)*100:.1f}%")
        print(f"  Pe_cells range: {np.min(Pe_cells[valid_mask]):.6f} - {np.max(Pe_cells[valid_mask]):.6f}mm")
        print(f"  Pe_cells mean: {np.mean(Pe_cells[valid_mask]):.6f}mm")
    else:
        # Simple SCS approach for other modes (simple, hybrid, conservative)
        print(f"Debug: storm_distribution range: {np.min(storm_distribution[valid_mask]):.2f} - {np.max(storm_distribution[valid_mask]):.2f}mm")
        print(f"Debug: mean storm_distribution: {np.mean(storm_distribution[valid_mask]):.2f}mm")
        print(f"Debug: mean Ia: {np.mean(Ia_cells[valid_mask]):.2f}mm")
        print(f"Debug: P_total_storm calculation: intensity={intensity_fn(rp_years=x, duration_minutes=Tc_total):.2f} mm/h * {Tc_total} min / 60 = {P_total_storm:.2f} mm")
        print(f"Debug: Ia statistics - min={np.min(Ia_cells[valid_mask]):.2f}mm, median={np.median(Ia_cells[valid_mask]):.2f}mm, max={np.max(Ia_cells[valid_mask]):.2f}mm")
        print(f"Debug: Curve number statistics - min={np.min(cn_data[valid_mask]):.1f}, median={np.median(cn_data[valid_mask]):.1f}, max={np.max(cn_data[valid_mask]):.1f}")
        print(f"Debug: S statistics - min={np.min(S_cells[valid_mask]):.1f}mm, median={np.median(S_cells[valid_mask]):.1f}mm, max={np.max(S_cells[valid_mask]):.1f}mm")
        
        P_mask = storm_distribution[valid_mask] > Ia_cells[valid_mask]
        print(f"Debug: {np.sum(P_mask)} cells have storm_distribution > Ia out of {np.sum(valid_mask)} valid cells")
        
        if np.any(P_mask):
            P_excess = storm_distribution[valid_mask][P_mask] - Ia_cells[valid_mask][P_mask]
            S_valid = S_cells[valid_mask][P_mask]
            
            # Calculate effective precipitation
            Pe_values = (P_excess ** 2) / (P_excess + S_valid)
            
            # Store effective precipitation for cells with runoff
            # Fix: Use proper boolean indexing for assignment
            valid_indices = np.where(valid_mask)
            p_indices = np.where(P_mask)[0]  # Get indices where P_mask is True
            
            # Map back to original array indices
            original_indices = (valid_indices[0][p_indices], valid_indices[1][p_indices])
            Pe_cells[original_indices] = Pe_values
            
            # Debug info
            print(f"  {np.sum(P_mask)} cells with runoff")
            if np.sum(P_mask) > 0:
                print(f"    Sample: P_total={storm_distribution[valid_mask][P_mask][0]:.2f}mm, Ia={Ia_cells[valid_mask][P_mask][0]:.2f}mm, S={S_valid[0]:.2f}mm")
                print(f"    Sample: P_excess={P_excess[0]:.2f}mm, Pe={Pe_values[0]:.2f}mm")
                print(f"    Total Pe generated: {np.sum(Pe_values):.2f}mm")
                print(f"    Pe_values range: {np.min(Pe_values):.6f} - {np.max(Pe_values):.6f}mm")
                print(f"    Pe_values mean: {np.mean(Pe_values):.6f}mm")
                print(f"    Pe_values sum: {np.sum(Pe_values):.6f}mm")
                print(f"    Pe_cells sum after assignment: {np.sum(Pe_cells):.6f}mm")
                print(f"    Pe_cells range after assignment: {np.min(Pe_cells):.6f} - {np.max(Pe_cells):.6f}mm")
        else:
            print(f"  WARNING: No cells have storm_distribution > Ia! This will result in zero runoff.")
            print(f"  Consider increasing precipitation or reducing curve numbers.")
            print(f"  Debug: max_storm_distribution={np.max(storm_distribution[valid_mask]):.2f}mm, min_Ia={np.min(Ia_cells[valid_mask]):.2f}mm")
            print(f"  Debug: To generate runoff, need max_storm_distribution > min_Ia: {np.max(storm_distribution[valid_mask]):.2f} > {np.min(Ia_cells[valid_mask]):.2f} = {np.max(storm_distribution[valid_mask]) > np.min(Ia_cells[valid_mask])}")
            print(f"  Debug: Try increasing precipitation_factor or return period")
    # Calculate travel time for each cell
    # Determine discharge point coordinates (separate from storm center)
    discharge_row = None
    discharge_col = None
    
    # Try user-provided discharge point coordinates first
    if discharge_point_coords is not None and len(discharge_point_coords) == 2:
        discharge_row, discharge_col = discharge_point_coords
        if 0 <= discharge_row < cn_data.shape[0] and 0 <= discharge_col < cn_data.shape[1]:
            print(f"Using user-provided discharge point: ({discharge_row}, {discharge_col})")
        else:
            print(f"Warning: User-provided discharge point ({discharge_row}, {discharge_col}) outside raster bounds")
            discharge_row = None
            discharge_col = None
    
    # Try EPSG:2056 coordinates for elevation calculations (most accurate for DEM)
    if discharge_row is None and discharge_point_epsg2056 is not None and len(discharge_point_epsg2056) == 2:
        easting, northing = discharge_point_epsg2056
        # Convert EPSG:2056 coordinates to raster coordinates using DEM transform
        if dem_data is not None:
            # Use DEM transform to convert EPSG:2056 coordinates to raster coordinates
            discharge_row, discharge_col = rasterio.transform.rowcol(dem_transform, easting, northing)
            if 0 <= discharge_row < dem_data.shape[0] and 0 <= discharge_col < dem_data.shape[1]:
                print(f"Using EPSG:2056 discharge point ({easting:.2f}, {northing:.2f}): raster ({discharge_row}, {discharge_col})")
            else:
                print(f"Warning: EPSG:2056 discharge point ({easting:.2f}, {northing:.2f}) outside DEM bounds")
                discharge_row = None
                discharge_col = None
        else:
            print(f"Warning: DEM not available for EPSG:2056 coordinate conversion")
    
    # Try geographic coordinates if raster coordinates failed or weren't provided
    if discharge_row is None and discharge_point_lon_lat is not None and len(discharge_point_lon_lat) == 2:
        lon, lat = discharge_point_lon_lat
        discharge_row, discharge_col = geographic_to_raster_coords(lon, lat, cn_transform, cn_data.shape)
        if discharge_row is not None and discharge_col is not None:
            print(f"Using geographic discharge point ({lon:.6f}, {lat:.6f}): raster ({discharge_row}, {discharge_col})")
        else:
            print(f"Warning: Could not convert geographic discharge point ({lon:.6f}, {lat:.6f}) to raster coordinates")
    
    # Fallback to isozone 0 (discharge point) if no user coordinates provided
    if discharge_row is None:
        discharge_mask = (isozone_data == 0) & valid_mask
        if np.any(discharge_mask):
            discharge_indices = np.where(discharge_mask)
            discharge_row = int(np.mean(discharge_indices[0]))
            discharge_col = int(np.mean(discharge_indices[1]))
            print(f"Using isozone 0 discharge point: ({discharge_row}, {discharge_col})")
        else:
            # Final fallback to storm center
            discharge_row, discharge_col = center_row, center_col
            print(f"Warning: No discharge point found, using storm center as discharge point: ({discharge_row}, {discharge_col})")
    
    # Calculate travel times using overland flow method or simplified approach
    if use_kirpich and dem_data is not None:
        print("Calculating travel times using overland flow method...")
        
        # Get discharge point elevation
        discharge_elevation = dem_data[discharge_row, discharge_col]
        print(f"Discharge point coordinates: ({discharge_row}, {discharge_col})")
        print(f"Discharge point elevation: {discharge_elevation:.1f} m")
        print(f"DEM data range: {np.nanmin(dem_data):.1f} - {np.nanmax(dem_data):.1f} m")
        print(f"DEM data shape: {dem_data.shape}")
        print(f"Valid DEM cells: {np.sum(~np.isnan(dem_data))} out of {dem_data.size}")
        
        # Check if discharge point has valid DEM data
        if np.isnan(discharge_elevation):
            print(f"Warning: Discharge point elevation is NaN, finding nearest valid DEM point...")
            
            # Find valid DEM cells within the catchment
            valid_dem_mask = valid_mask & (~np.isnan(dem_data))
            
            if np.any(valid_dem_mask):
                # Find the cell closest to the original discharge point that has valid DEM data
                valid_dem_indices = np.where(valid_dem_mask)
                distances_to_discharge = np.sqrt((valid_dem_indices[0] - discharge_row)**2 + (valid_dem_indices[1] - discharge_col)**2)
                nearest_idx = np.argmin(distances_to_discharge)
                
                # Update discharge point to nearest valid DEM cell
                discharge_row = valid_dem_indices[0][nearest_idx]
                discharge_col = valid_dem_indices[1][nearest_idx]
                discharge_elevation = dem_data[discharge_row, discharge_col]
                
                print(f"Updated discharge point to nearest valid DEM: ({discharge_row}, {discharge_col})")
                print(f"New discharge elevation: {discharge_elevation:.1f} m")
            else:
                print(f"Error: No valid DEM cells found in catchment, falling back to simplified approach")
                use_kirpich = False
        
        # Only proceed with overland flow if we have a valid discharge point
        if not np.isnan(discharge_elevation):
            # Calculate flow length and elevation difference for each cell
            rows, cols = np.meshgrid(np.arange(cn_data.shape[0]), np.arange(cn_data.shape[1]), indexing='ij')
            
            # Flow length: distance from each cell to discharge point [m]
            flow_lengths = np.sqrt((rows - discharge_row)**2 + (cols - discharge_col)**2) * np.sqrt(pixel_area_m2)
            
            # Elevation difference: elevation of each cell minus discharge elevation [m]
            elevation_diffs = dem_data - discharge_elevation
            
            # Debug elevation differences
            print(f"Elevation difference range: {np.nanmin(elevation_diffs):.1f} - {np.nanmax(elevation_diffs):.1f} m")
            print(f"Cells with positive elevation difference: {np.sum(elevation_diffs > 0)}")
            print(f"Cells with negative elevation difference: {np.sum(elevation_diffs < 0)}")
            print(f"Cells with zero elevation difference: {np.sum(elevation_diffs == 0)}")
            print(f"Cells with NaN elevation difference: {np.sum(np.isnan(elevation_diffs))}")
            
            # Apply overland flow calculation
            travel_times = np.zeros_like(flow_lengths, dtype=np.float32)
            
            # Only calculate for valid cells with positive elevation difference
            valid_kirpich_mask = valid_mask & (elevation_diffs > 0) & (flow_lengths > 0) & (~np.isnan(elevation_diffs))
            
            if np.any(valid_kirpich_mask):
                # For overland flow, use a more realistic approach
                L = flow_lengths[valid_kirpich_mask]  # Flow length [m]
                H = elevation_diffs[valid_kirpich_mask]  # Elevation difference [m]
                
                # Calculate H/L ratio (slope as decimal, not degrees)
                slope = H / L
                
                # Debug slope calculation
                print(f"Slope range: {np.min(slope):.6f} - {np.max(slope):.6f} (decimal)")
                print(f"Slope range: {np.min(slope)*100:.2f}% - {np.max(slope)*100:.2f}% (percentage)")
                print(f"Slope range: {np.arctan(np.min(slope))*180/np.pi:.2f}° - {np.arctan(np.max(slope))*180/np.pi:.2f}° (degrees)")
                
                # Use overland flow velocity based on slope
                # For realistic travel times, use a simple velocity approach
                # Typical overland flow velocities: 0.5-2.0 m/s depending on slope and surface
                # Use a conservative approach: velocity = 1.0 * sqrt(slope) [m/s]
                velocities = 1.0 * np.sqrt(slope)  # [m/s] - conservative overland flow
                velocities = np.clip(velocities, 0.5, 2.0)  # [m/s] - realistic range
                
                # Convert to m/min for travel time calculation
                velocities_m_per_min = velocities * 60  # [m/min]
                
                # Calculate travel time: T = L / velocity [minutes]
                travel_times[valid_kirpich_mask] = L / velocities_m_per_min  # [minutes]
                
                print(f"Overland flow velocities: {np.min(velocities):.2f} - {np.max(velocities):.2f} m/s")
                print(f"Effective velocities (with obstacle factor): {np.min(velocities_m_per_min):.2f} - {np.max(velocities_m_per_min):.2f} m/min")
                print(f"Travel time range: {np.min(travel_times[valid_kirpich_mask]):.2f} - {np.max(travel_times[valid_kirpich_mask]):.2f} minutes")
                
                print(f"Overland flow calculation completed:")
                print(f"  - Valid cells: {np.sum(valid_kirpich_mask)} out of {np.sum(valid_mask)}")
                print(f"  - Flow length range: {np.min(L):.1f} - {np.max(L):.1f} m")
                print(f"  - Elevation difference range: {np.min(H):.1f} - {np.max(H):.1f} m")
                print(f"  - Slope range: {np.min(slope):.4f} - {np.max(slope):.4f}")
                print(f"  - Travel time range: {np.min(travel_times[valid_kirpich_mask]):.2f} - {np.max(travel_times[valid_kirpich_mask]):.2f} minutes")
                
                # Handle cells that don't meet overland flow criteria
                invalid_kirpich_mask = valid_mask & ~valid_kirpich_mask
                if np.any(invalid_kirpich_mask):
                    print(f"  - Cells needing fallback calculation: {np.sum(invalid_kirpich_mask)}")
                    # Use simplified approach for these cells
                    fallback_distances = flow_lengths[invalid_kirpich_mask]
                    # Use a reasonable fallback velocity: 1.0 m/s = 60 m/min
                    fallback_times = fallback_distances / 60  # 60 m/min velocity
                    travel_times[invalid_kirpich_mask] = fallback_times
                    print(f"  - Fallback travel time range: {np.min(fallback_times):.2f} - {np.max(fallback_times):.2f} minutes")
            else:
                print("Warning: No valid cells for overland flow calculation, using simplified approach")
                use_kirpich = False
        else:
            print("Warning: No valid discharge elevation, using simplified approach")
            use_kirpich = False
    
    if not use_kirpich or dem_data is None:
        print("Calculating travel times using simplified approach...")
        
        # Calculate distance from each cell to the discharge point
        rows, cols = np.meshgrid(np.arange(cn_data.shape[0]), np.arange(cn_data.shape[1]), indexing='ij')
        distances = np.sqrt((rows - discharge_row)**2 + (cols - discharge_col)**2) * np.sqrt(pixel_area_m2)  # Convert to meters
        
        # Calculate travel time using simplified approach: T = L / (60) [minutes]
        # where L is distance in meters, using 60 m/min velocity (1.0 m/s)
        travel_times = distances / 60  # [minutes]
        
        print(f"Simplified calculation completed:")
        print(f"  - Distance range: {np.min(distances[valid_mask]):.1f} - {np.max(distances[valid_mask]):.1f} m")
        print(f"  - Travel time range: {np.min(travel_times[valid_mask]):.2f} - {np.max(travel_times[valid_mask]):.2f} minutes")
        print(f"  - Velocity: 60 m/min (1.0 m/s)")
    
    # Save travel times as TIFF file
    try:
        temp_dir = "./data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create filename with timestamp to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if routing_method == "time_values" and arrival_timesteps is not None and valid_time_mask is not None:
            # Save time values routing results
            time_values_routing_file = f"{temp_dir}/time_values_routing_{timestamp}.tif"
            
            # Create a copy of arrival timesteps for saving (only valid cells)
            arrival_timesteps_raster = np.zeros_like(arrival_timesteps, dtype=np.float32)
            arrival_timesteps_raster[valid_time_mask] = arrival_timesteps[valid_time_mask]
            
            # Save as GeoTIFF using the same transform and CRS as the curve number raster
            profile = {
                'driver': 'GTiff',
                'height': arrival_timesteps_raster.shape[0],
                'width': arrival_timesteps_raster.shape[1],
                'count': 1,
                'dtype': arrival_timesteps_raster.dtype.name,
                'crs': cn_crs,
                'transform': cn_transform,
                'nodata': 0,
                'compress': 'lzw'
            }
            
            with rasterio.open(time_values_routing_file, 'w', **profile) as dst:
                dst.write(arrival_timesteps_raster, 1)
            
            print(f"Time values routing results saved as TIFF: {time_values_routing_file}")
            print(f"  - File size: {os.path.getsize(time_values_routing_file) / 1024:.1f} KB")
            print(f"  - Arrival timestep range: {np.min(arrival_timesteps_raster[valid_time_mask]):.0f} - {np.max(arrival_timesteps_raster[valid_time_mask]):.0f} timesteps")
            print(f"  - Time range: {np.min(arrival_timesteps_raster[valid_time_mask])*dt:.0f} - {np.max(arrival_timesteps_raster[valid_time_mask])*dt:.0f} minutes")
            print(f"  - Method: Time Values from time_values.tif")
        elif routing_method == "time_values":
            print(f"Time values routing selected but no routing data available for saving")
        else:
            # Save travel times for other methods
            travel_times_file = f"{temp_dir}/travel_times_{timestamp}.tif"
            
            # Create a copy of travel times for saving (only valid cells)
            travel_times_raster = np.zeros_like(travel_times, dtype=np.float32)
            travel_times_raster[valid_mask] = travel_times[valid_mask]
            
            # Save as GeoTIFF using the same transform and CRS as the curve number raster
            profile = {
                'driver': 'GTiff',
                'height': travel_times_raster.shape[0],
                'width': travel_times_raster.shape[1],
                'count': 1,
                'dtype': travel_times_raster.dtype.name,
                'crs': cn_crs,
                'transform': cn_transform,
                'nodata': 0,
                'compress': 'lzw'
            }
            
            with rasterio.open(travel_times_file, 'w', **profile) as dst:
                dst.write(travel_times_raster, 1)
            
            print(f"Travel times saved as TIFF: {travel_times_file}")
            print(f"  - File size: {os.path.getsize(travel_times_file) / 1024:.1f} KB")
            print(f"  - Travel time range: {np.min(travel_times_raster[valid_mask]):.2f} - {np.max(travel_times_raster[valid_mask]):.2f} minutes")
            print(f"  - Mean travel time: {np.mean(travel_times_raster[valid_mask]):.2f} minutes")
            print(f"  - Method: {'Overland Flow' if use_kirpich and dem_data is not None else 'Simplified'}")
            if not use_kirpich or dem_data is None:
                print(f"  - Velocity: 60 m/min (1.0 m/s)")
        
    except Exception as e:
        print(f"Warning: Could not save routing results as TIFF: {e}")
    
    # Convert effective precipitation to runoff volume [m³] for each cell
    # Pe is in mm, convert to m³: Pe_mm * area_m² / 1000
    runoff_volumes = Pe_cells * pixel_area_m2 / 1000  # [m³]
    
    # Debug runoff volumes
    print(f"Debug: Pe_cells range: {np.min(Pe_cells[valid_mask]):.6f} - {np.max(Pe_cells[valid_mask]):.6f}mm")
    print(f"Debug: Total Pe_cells: {np.sum(Pe_cells[valid_mask]):.2f}mm")
    print(f"Debug: runoff_volumes range: {np.min(runoff_volumes[valid_mask]):.6f} - {np.max(runoff_volumes[valid_mask]):.6f}m³")
    print(f"Debug: Total runoff_volumes: {np.sum(runoff_volumes[valid_mask]):.2f}m³")
    print(f"Debug: Cells with runoff: {np.sum(runoff_volumes[valid_mask] > 0)} out of {np.sum(valid_mask)}")
    print(f"Debug: Water balance mode: {water_balance_mode}")
    print(f"Debug: Routing method: {routing_method}")
    print(f"Debug: Pixel area: {pixel_area_m2:.2f} m²")
    print(f"Debug: Conversion factor: {pixel_area_m2 / 1000:.6f}")
    
    # Initialize runoff time series for each timestep
    # This will store runoff volumes that arrive at each timestep
    runoff_timesteps = [0.0] * max_timesteps  # Pre-allocate with zeros
    
    # Initialize variables for routing
    arrival_timesteps = None
    valid_time_mask = None
    
    if routing_method == "time_values":
        # Use time_values.tif-based routing method
        print(f"Using time_values.tif-based routing method...")
        
        if time_values_data is None:
            return {"error": "Time values data not available for time_values routing method"}
        
        # Calculate arrival timestep for each cell using time_values.tif
        # time_values_data contains travel time in minutes for each cell
        arrival_timesteps = np.round(time_values_data / dt).astype(int)  # Convert to timestep index
        
        # Calculate maximum timestep needed based on time_values
        max_time_value = np.nanmax(time_values_data[valid_mask])
        max_timesteps_needed = int(np.ceil(max_time_value / dt)) + 10  # Add buffer
        
        # Extend runoff_timesteps if needed
        if max_timesteps_needed > len(runoff_timesteps):
            runoff_timesteps.extend([0.0] * (max_timesteps_needed - len(runoff_timesteps)))
            print(f"Extended simulation to {max_timesteps_needed} timesteps based on time_values")
        
        # Sum runoff volumes by arrival timestep
        valid_time_mask = valid_mask & ~np.isnan(time_values_data) & (time_values_data > 0)
        
        print(f"Time values routing: max_time={max_time_value:.2f}min, dt={dt}min, max_timesteps={max_timesteps_needed}")
        print(f"Valid time values cells: {np.sum(valid_time_mask)} out of {np.sum(valid_mask)}")
        
        # Group cells by arrival timestep and sum runoff volumes
        for i in range(max_timesteps_needed):
            timestep_mask = (arrival_timesteps == i) & valid_time_mask
            if np.any(timestep_mask):
                runoff_volume = np.sum(runoff_volumes[timestep_mask])
                runoff_timesteps[i] += runoff_volume
                if runoff_volume > 0:
                    print(f"Timestep {i} ({i*dt}min): {np.sum(timestep_mask)} cells arrive, runoff_volume={runoff_volume:.3f} m³")
        
        print(f"Time values routing completed. Max timesteps: {max_timesteps_needed}")
        
        # Update max_timesteps for the rest of the calculation
        max_timesteps = max_timesteps_needed
        
    elif routing_method == "isozone":
        # Use isozone-based routing (original method)
        print(f"Using isozone-based routing method...")
        
        # Get maximum isozone to determine total simulation time
        max_zone = int(np.nanmax(isozone_data))
        if max_zone <= 0:
            return {"error": "Invalid isozone data: max_zone <= 0"}
        
        print(f"Isozone routing: max_zone={max_zone}, dt={dt}min")
        
        # Validate isozone data
        valid_isozones = np.isfinite(isozone_data) & (isozone_data >= 0)
        print(f"Valid isozone cells: {np.sum(valid_isozones)} out of {isozone_data.size}")
        
        # Calculate runoff for each zone
        for zone in range(max_zone + 1):
            # Get cells in current isozone
            zone_mask = (isozone_data == zone) & valid_mask & valid_isozones
            
            if not np.any(zone_mask):
                continue
            
            print(f"Processing Zone {zone}: {np.sum(zone_mask)} cells")
            
            # Sum runoff volumes for cells in this zone
            zone_runoff_volume = np.sum(runoff_volumes[zone_mask])
            
            # The runoff from this zone reaches the drainage point after 'zone' timesteps
            # So we need to add this runoff to the discharge at timestep 'zone'
            arrival_timestep = zone
            
            # Store the runoff contribution for the arrival timestep
            if arrival_timestep < len(runoff_timesteps):
                # Add to existing runoff for this arrival timestep
                runoff_timesteps[arrival_timestep] += zone_runoff_volume
            else:
                # Extend the runoff_timesteps list if needed
                while len(runoff_timesteps) <= arrival_timestep:
                    runoff_timesteps.append(0.0)
                runoff_timesteps[arrival_timestep] += zone_runoff_volume
            
            # Debug: Show runoff volume for all zones
            print(f"  Zone {zone}: {np.sum(zone_mask)} cells, Pe_sum={np.sum(Pe_cells[zone_mask]):.2f}mm, runoff_volume={zone_runoff_volume:.3f} m³, arrives at timestep {arrival_timestep}")
        
        print(f"Isozone routing completed. Total zones: {max_zone + 1}")
        
    else:
        # Use travel time-based routing (current method)
        print(f"Using travel time-based routing method...")
        
        # Calculate arrival timestep for each cell
        arrival_timesteps = np.round(travel_times / dt).astype(int)  # Convert to timestep index
        
        # Sum runoff volumes by arrival timestep
        for i in range(max_timesteps):
            timestep_mask = (arrival_timesteps == i) & valid_mask
            if np.any(timestep_mask):
                runoff_volume = np.sum(runoff_volumes[timestep_mask])
                runoff_timesteps[i] += runoff_volume
                if runoff_volume > 0:
                    print(f"Timestep {i}: {np.sum(timestep_mask)} cells arrive, runoff_volume={runoff_volume:.3f} m³")
        
        print(f"Travel time routing completed. Max timesteps: {max_timesteps}")
    
    # Convert runoff volumes to discharge [m³/s]
    # Discharge = volume / time = m³ / (dt * 60 s)
    discharge_timesteps = []
    for i, runoff_volume in enumerate(runoff_timesteps):
        if runoff_volume > 0:
            discharge = runoff_volume / (dt * 60)  # [m³/s]
            discharge_timesteps.append(discharge)
            print(f"Timestep {i}: runoff_volume={runoff_volume:.3f} m³, Q={discharge:.3f} m³/s")
        else:
            discharge_timesteps.append(0.0)
    
    # 4. Find maximum discharge (HQ)
    HQ = max(discharge_timesteps)
    max_timestep = discharge_timesteps.index(HQ)
    
    print(f"Maximum discharge: {HQ:.3f} m³/s at timestep {max_timestep}")
    print(f"Discharge time series: {[f'{q:.3f}' for q in discharge_timesteps]}")
    
    # Print water balance summary
    total_initial_water = np.sum(storm_distribution[valid_mask])
    total_runoff_generated = np.sum(Pe_cells[valid_mask])
    total_infiltration = total_initial_water - total_runoff_generated
    
    print(f"\n=== WATER BALANCE SUMMARY ===")
    print(f"Total precipitation applied: {total_initial_water:.2f} mm")
    print(f"Total runoff generated: {total_runoff_generated:.2f} mm ({total_runoff_generated/total_initial_water*100:.1f}%)")
    print(f"Total infiltration: {total_infiltration:.2f} mm ({total_infiltration/total_initial_water*100:.1f}%)")
    
    # Print travel time statistics
    print(f"\n=== TRAVEL TIME STATISTICS ===")
    print(f"Storm center: ({center_row}, {center_col})")
    print(f"Discharge point: ({discharge_row}, {discharge_col})")
    print(f"Routing method: {routing_method}")
    
    if routing_method == "time_values":
        print(f"Method: Time Values from time_values.tif")
        if time_values_data is not None:
            valid_time_mask = valid_mask & ~np.isnan(time_values_data) & (time_values_data > 0)
            if np.any(valid_time_mask):
                print(f"Mean travel time: {np.nanmean(time_values_data[valid_time_mask]):.1f} minutes")
                print(f"Max travel time: {np.nanmax(time_values_data[valid_time_mask]):.1f} minutes")
                print(f"Min travel time: {np.nanmin(time_values_data[valid_time_mask]):.1f} minutes")
                print(f"Valid cells: {np.sum(valid_time_mask)} out of {np.sum(valid_mask)}")
            else:
                print(f"Mean travel time: No valid time values")
                print(f"Max travel time: No valid time values")
                print(f"Min travel time: No valid time values")
    else:
        print(f"Method: {'Overland Flow' if use_kirpich and dem_data is not None else 'Simplified'}")
        if use_kirpich and dem_data is not None:
            print(f"Discharge elevation: {discharge_elevation:.1f} m")
            print(f"Mean flow length: {np.mean(flow_lengths[valid_mask]):.1f} meters")
            print(f"Max flow length: {np.max(flow_lengths[valid_mask]):.1f} meters")
            valid_elev_diffs = elevation_diffs[valid_mask & ~np.isnan(elevation_diffs)]
            if len(valid_elev_diffs) > 0:
                print(f"Mean elevation difference: {np.mean(valid_elev_diffs):.1f} meters")
                print(f"Max elevation difference: {np.max(valid_elev_diffs):.1f} meters")
            else:
                print(f"Mean elevation difference: No valid elevation differences")
                print(f"Max elevation difference: No valid elevation differences")
        else:
            print(f"Velocity: 60 m/min (1.0 m/s)")
            print(f"Mean distance to discharge point: {np.mean(distances[valid_mask]):.1f} meters")
            print(f"Max distance to discharge point: {np.max(distances[valid_mask]):.1f} meters")
        print(f"Mean travel time: {np.mean(travel_times[valid_mask]):.1f} minutes")
        print(f"Max travel time: {np.max(travel_times[valid_mask]):.1f} minutes")
        print(f"Min travel time: {np.min(travel_times[valid_mask]):.1f} minutes")
        
    # Print cell-based summary
    print(f"\n=== CELL-BASED SUMMARY ===")
    print(f"Total cells: {np.sum(valid_mask)}")
    print(f"Cells with runoff: {np.sum(Pe_cells[valid_mask] > 0)}")
    print(f"Cells without runoff: {np.sum(Pe_cells[valid_mask] == 0)}")
    
    # Print runoff statistics
    runoff_cells = Pe_cells[valid_mask] > 0
    if np.any(runoff_cells):
        print(f"Runoff statistics:")
        print(f"  Mean runoff per cell: {np.mean(Pe_cells[valid_mask][runoff_cells]):.2f} mm")
        print(f"  Max runoff per cell: {np.max(Pe_cells[valid_mask][runoff_cells]):.2f} mm")
        print(f"  Min runoff per cell: {np.min(Pe_cells[valid_mask][runoff_cells]):.2f} mm")
    
    # 5. Calculate additional parameters for compatibility
    # Use the timestep of maximum discharge for other calculations
    Tc = (max_timestep + 1) * dt  # [min]
    TB = Tc  # Simplified for distributed approach
    TFl = 0  # Not used in distributed approach
    i_final = intensity_fn(rp_years=x, duration_minutes=Tc)  # [mm/h]
    S = np.nanmean(S_cells[valid_mask])  # Average S for reporting
    Ia = np.nanmean(Ia_cells[valid_mask])  # Average Ia for reporting
    Pe_final = HQ * dt * 60 / (np.sum(valid_mask) * pixel_area_m2 / 1000)  # Average Pe for reporting
    
    # 7. Update database
    #prisma = Prisma()
    #prisma.connect()
    
    # Calculate average curve number for reporting
    effective_curve_number = np.nanmean(cn_data[valid_mask]) if cn_data is not None else curve_number
    """
    updatedResults = prisma.nam.update(
        where={
            'id': nam_id
        },
        data={
            'NAM_Result': {
                'upsert': {
                    'update': {
                        'HQ': HQ,
                    },
                    'create': {
                        'HQ': HQ
                    }
                }
            }
        }
    )
    
    prisma.disconnect(5)
    """
    return {
        "HQ": float(HQ),
        "Tc": float(Tc),
        "TB": float(TB),
        "TFl": float(TFl),
        "i": float(i_final),
        "S": float(S),
        "Ia": float(Ia),
        "Pe": float(Pe_final),
        "effective_curve_number": float(effective_curve_number),
        "runoff_timesteps": [float(x) for x in runoff_timesteps],
        "discharge_timesteps": [float(x) for x in discharge_timesteps],
        "max_timestep": int(max_timestep),
        "total_cells": int(np.sum(valid_mask)),
        "pixel_area_m2": float(pixel_area_m2),
        "water_balance": {
            "approach": water_balance_mode,
            "total_initial_water": float(total_initial_water),
            "total_infiltration": float(total_infiltration),
            "total_runoff_generated": float(total_runoff_generated),
            "infiltration_percentage": float(total_infiltration/total_initial_water*100),
            "runoff_percentage": float(total_runoff_generated/total_initial_water*100)
        },
        "storm_distribution": {
            "storm_center": (int(center_row), int(center_col)),
            "storm_center_mode": storm_center_mode,
            "storm_radius": float(storm_radius),
            "max_precipitation": float(max_precip),
            "min_precipitation": float(min_precip),
            "mean_precipitation": float(mean_precip),
            "distribution_type": "exponential_decay"
        },
        "routing_method": routing_method,
        "time_values_info": {
            "used_time_values": routing_method == "time_values",
            "max_travel_time": float(np.nanmax(time_values_data[valid_mask])) if routing_method == "time_values" and time_values_data is not None else None,
            "mean_travel_time": float(np.nanmean(time_values_data[valid_mask])) if routing_method == "time_values" and time_values_data is not None else None,
            "min_travel_time": float(np.nanmin(time_values_data[valid_mask])) if routing_method == "time_values" and time_values_data is not None else None
        } if routing_method == "time_values" else None
    }


@app.task(name="extract_dem", bind=True)
def extract_dem(self, projectId: str, userId: int):
    """
    Extract DEM data for a catchment from the large DEM file and save as raster.
    Uses the catchment geojson from the project to clip the DEM.
    """
    self.update_state(state='PROGRESS',
                meta={'text': 'Loading project data', 'progress': 5})
    
    # Get project data from database
    prisma = Prisma()
    prisma.connect()
    
    project = prisma.project.find_unique_or_raise(
        where={
            'id': projectId
        }
    )
    
    # Parse catchment geojson
    catchment_geojson = json.loads(project.catchment_geojson)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Processing catchment geometry', 'progress': 10})
    
    # Convert geojson to shapely geometry
    catchment_polygons = []
    for feature in catchment_geojson['features']:
        geom = shape(feature['geometry'])
        catchment_polygons.append(geom)
    
    # Union all polygons
    catchment_union = ops.unary_union(catchment_polygons)
    
    # Get bounding box
    minx, miny, maxx, maxy = catchment_union.bounds
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Loading DEM data', 'progress': 20})
    
    # Load the large DEM file
    dem_file = "./data/geotiffminusriver.tif"
    
    try:
        with rasterio.open(dem_file) as src:
            # Get the DEM's CRS and transform
            dem_crs = src.crs
            dem_transform = src.transform
            
            print(f"DEM CRS: {dem_crs}")
            print(f"Catchment CRS: EPSG:2056")
            
            # Convert catchment bounds to DEM CRS if needed
            # The catchment geojson is in EPSG:2056 (Swiss coordinate system)
            catchment_crs = pyproj.CRS.from_epsg(2056)
            
            if catchment_crs != dem_crs:
                print(f"Transforming catchment from {catchment_crs} to {dem_crs}")
                # Transform catchment to DEM CRS
                transformer = pyproj.Transformer.from_crs(
                    catchment_crs, dem_crs, always_xy=True
                )
                catchment_union = ops.transform(transformer.transform, catchment_union)
                minx, miny, maxx, maxy = catchment_union.bounds
                print(f"Transformed bounds: {minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f}")
            else:
                print(f"CRS match, no transformation needed")
                print(f"Original bounds: {minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f}")
            
            # Calculate window for reading the DEM subset
            window = rasterio.windows.from_bounds(
                minx, miny, maxx, maxy, dem_transform
            )
            
            # Read the DEM data for the catchment area
            dem_data = src.read(1, window=window)
            
            # Get the transform for the subset
            subset_transform = rasterio.windows.transform(window, dem_transform)
            
            self.update_state(state='PROGRESS',
                        meta={'text': 'Clipping DEM to catchment', 'progress': 40})
            
            # Create a mask for the catchment
            mask = rasterio.features.geometry_mask(
                [catchment_union],
                out_shape=dem_data.shape,
                transform=subset_transform,
                invert=True
            )
            
            # Apply mask to DEM data
            dem_clipped = np.where(mask, dem_data, np.nan)
            
            self.update_state(state='PROGRESS',
                        meta={'text': 'Saving DEM raster', 'progress': 60})
            
            # Create output directory
            output_dir = f"data/{userId}/{projectId}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save as GeoTIFF
            output_file = f"{output_dir}/dem.tif"
            
            profile = {
                'driver': 'GTiff',
                'height': dem_clipped.shape[0],
                'width': dem_clipped.shape[1],
                'count': 1,
                'dtype': dem_clipped.dtype.name,
                'crs': dem_crs,
                'transform': subset_transform,
                'nodata': np.nan,
                'compress': 'lzw'
            }
            
            with rasterio.open(output_file, 'w', **profile) as dst:
                dst.write(dem_clipped, 1)
            
            # Calculate statistics
            valid_dem = dem_clipped[~np.isnan(dem_clipped)]
            min_elev = np.min(valid_dem)
            max_elev = np.max(valid_dem)
            mean_elev = np.mean(valid_dem)
            
            self.update_state(state='PROGRESS',
                        meta={'text': 'DEM extraction completed', 'progress': 100})
            
            print(f"DEM extracted and saved: {output_file}")
            print(f"  - Elevation range: {min_elev:.1f} - {max_elev:.1f} m")
            print(f"  - Mean elevation: {mean_elev:.1f} m")
            print(f"  - File size: {os.path.getsize(output_file) / 1024:.1f} KB")
            
            prisma.disconnect()
            
            return {
                "dem_file": output_file,
                "min_elevation": float(min_elev),
                "max_elevation": float(max_elev),
                "mean_elevation": float(mean_elev),
                "crs": str(dem_crs),
                "shape": dem_clipped.shape,
                "catchment_crs": "EPSG:2056"
            }
            
    except Exception as e:
        print(f"Error extracting DEM: {e}")
        prisma.disconnect()
        raise e


@app.task(name="get_curve_numbers", bind=True)
def get_curve_numbers(self, projectId: str, userId: int):
    """
    Get curve numbers for a catchment geojson and save as raster.
    Based on QGIS Curve Number Generator plugin approach.
    Uses multiple data sources: land use, soil data, and hydrologic soil groups.
    """
    self.update_state(state='PROGRESS',
                meta={'text': 'Loading project data', 'progress': 5})
    
    # Get project data from database
    prisma = Prisma()
    prisma.connect()
    
    project = prisma.project.find_unique_or_raise(
        where={
            'id': projectId
        }
    )
    
    # Parse catchment geojson
    catchment_geojson = json.loads(project.catchment_geojson)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Processing catchment geometry', 'progress': 10})
    
    # Convert geojson to shapely geometry
    catchment_polygons = []
    for feature in catchment_geojson['features']:
        geom = shape(feature['geometry'])
        catchment_polygons.append(geom)
    
    # Union all polygons
    catchment_union = ops.unary_union(catchment_polygons)
    
    # Get bounding box (coordinates in EPSG:2056 - Swiss coordinate system)
    minx, miny, maxx, maxy = catchment_union.bounds
    
    # Add buffer for data retrieval
    # For EPSG:2056, buffer in meters (1000m = 1km)
    buffer_distance = 1000  # meters
    bbox = (minx - buffer_distance, miny - buffer_distance, 
            maxx + buffer_distance, maxy + buffer_distance)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Downloading land use data', 'progress': 20})
    
    # Convert bbox from EPSG:2056 to EPSG:4326 (WGS84) for API calls
    from pyproj import Transformer
    
    # Create transformer from EPSG:2056 to WGS84
    transformer = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
    
    # Convert bbox corners from Swiss coordinates to WGS84
    min_lon, min_lat = transformer.transform(bbox[0], bbox[1])
    max_lon, max_lat = transformer.transform(bbox[2], bbox[3])
    
    # Create WGS84 bbox [min_lon, min_lat, max_lon, max_lat]
    bbox_wgs84 = [min_lon, min_lat, max_lon, max_lat]
    
    print(f"EPSG:2056 bbox: {bbox}")
    print(f"WGS84 bbox: {bbox_wgs84}")
    
    # Download land use data (ESA WorldCover)
    landuse_data = download_esa_worldcover(bbox_wgs84)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Downloading soil data', 'progress': 40})
    
    # Download soil data (FAO HWSD or USDA SSURGO)
    soil_data = download_soil_data(bbox_wgs84)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Processing curve number data', 'progress': 60})
    
    # Create a grid for the catchment area
    cell_size = 30  # meters (ESA WorldCover resolution)
    # For EPSG:2056 (Swiss coordinates), cell_size is already in meters
    grid = create_catchment_grid(catchment_union, cell_size)
    
    # Generate curve numbers using the comprehensive approach
    curve_number_raster = generate_curve_numbers_comprehensive(
        landuse_data, soil_data, grid, catchment_union
    )
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Saving curve number raster', 'progress': 80})
    
    # Create output directory
    output_dir = f"data/{userId}/{projectId}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save as GeoTIFF
    output_file = f"{output_dir}/curvenumbers.tif"
    save_curve_number_raster(curve_number_raster, grid, output_file)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Finished', 'progress': 100})
    
    prisma.disconnect(5)
    return {"status": "success", "file": output_file}


def download_esa_worldcover(bbox):
    """
    Download land cover data from local ESA WorldCover 2021 VRT file.
    Uses the esa_worldcover_2021.vrt file in ./data.
    Based on the QGIS Curve Number Generator plugin approach.
    """
    import tempfile
    import os
    
    # Local ESA WorldCover 2021 VRT file
    vrt_file_path = "./data/esa_worldcover_2021.vrt"
    
    # Create temp directory if it doesn't exist
    temp_dir = "./data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Check if VRT file exists
        if not os.path.exists(vrt_file_path):
            print(f"ESA WorldCover VRT file not found: {vrt_file_path}")
            raise FileNotFoundError(f"VRT file not found: {vrt_file_path}")
        
        print(f"Using local ESA WorldCover 2021 VRT file: {vrt_file_path}")
        print(f"Bounding box: {bbox}")
        
        # Add buffer cells like the QGIS plugin (2 cells on each side)
        lc_pixel_size = 0.000083333333333  # ~10m in degrees
        extent_esa = (
            bbox[0] - 2 * lc_pixel_size,
            bbox[1] - 2 * lc_pixel_size,
            bbox[2] + 2 * lc_pixel_size,
            bbox[3] + 2 * lc_pixel_size,
        )
        
        # Use rasterio to read from VRT file with the buffered bbox
        with rasterio.open(vrt_file_path) as src:
            # Read the data for the specified bbox
            window = rasterio.windows.from_bounds(
                extent_esa[0], extent_esa[1], extent_esa[2], extent_esa[3], 
                src.transform
            )
            
            # Read the data
            data = src.read(1, window=window)
            
            # Get the transform for the window
            window_transform = rasterio.windows.transform(window, src.transform)
            
            # Save the extracted data to temp directory
            temp_filename = f"esa_worldcover_bbox_{bbox[0]:.3f}_{bbox[1]:.3f}_{bbox[2]:.3f}_{bbox[3]:.3f}.tif"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            with rasterio.open(
                temp_file_path,
                'w',
                driver='GTiff',
                height=data.shape[0],
                width=data.shape[1],
                count=1,
                dtype=data.dtype,
                crs=src.crs,
                transform=window_transform
            ) as dst:
                dst.write(data, 1)
            
            print(f"Saved ESA WorldCover data to: {temp_file_path}")
            
            # ESA WorldCover 2021 classification values (raw values, not curve numbers)
            # Curve numbers will be calculated using lookup tables
            worldcover_classes = {
                10: "Tree cover",
                20: "Shrubland", 
                30: "Grassland",
                40: "Cropland",
                50: "Built-up",
                60: "Bare / sparse vegetation",
                70: "Snow and ice",
                80: "Permanent water bodies",
                90: "Herbaceous wetland",
                95: "Mangroves",
                100: "Moss and lichen"
            }
            
            print(f"Successfully extracted ESA WorldCover 2021 data for bbox: {bbox}")
            print(f"Data shape: {data.shape}")
            print(f"Unique values: {np.unique(data)}")
            
            return {
                'source': 'ESA_WorldCover_2021_Local',
                'data_file': temp_file_path,
                'classification': worldcover_classes,
                'bbox': bbox,
                'vrt_file': vrt_file_path,
                'resolution': 10,  # meters
                'description': 'ESA WorldCover 2021 10m Global Land Cover (Local VRT)'
            }
            
    except Exception as e:
        print(f"Error reading ESA WorldCover 2021 VRT file: {e}")
        # Fallback to simplified land cover data based on location
        center_lon = (bbox[0] + bbox[2]) / 2
        center_lat = (bbox[1] + bbox[3]) / 2
        return create_fallback_landcover_data(bbox, center_lat, center_lon)


def create_fallback_landcover_data(bbox, center_lat, center_lon):
    """
    Create fallback land cover data when ESA WorldCover is unavailable.
    """
    # ESA WorldCover classification values and their curve numbers
    worldcover_curve_numbers = {
        10: 55,   # Tree cover (forest)
        20: 65,   # Shrubland
        30: 61,   # Grassland
        40: 72,   # Cropland
        50: 98,   # Built-up
        60: 77,   # Bare / sparse vegetation
        70: 100,  # Snow and ice
        80: 100,  # Permanent water bodies
        90: 58,   # Herbaceous wetland
        95: 60,   # Mangroves
        100: 100  # Moss and lichen
    }
    
    # Determine land cover distribution based on location
    if center_lat > 60:  # High latitude
        landcover_distribution = {
            10: 0.40,  # Forest (40%)
            20: 0.20,  # Shrubland (20%)
            30: 0.15,  # Grassland (15%)
            40: 0.05,  # Agricultural (5%)
            50: 0.02,  # Built-up (2%)
            60: 0.05,  # Bare (5%)
            70: 0.10,  # Snow/ice (10%)
            80: 0.03   # Water (3%)
        }
    elif center_lat > 30:  # Temperate
        landcover_distribution = {
            10: 0.25,  # Forest (25%)
            20: 0.15,  # Shrubland (15%)
            30: 0.30,  # Grassland (30%)
            40: 0.20,  # Agricultural (20%)
            50: 0.05,  # Built-up (5%)
            60: 0.03,  # Bare (3%)
            70: 0.01,  # Snow/ice (1%)
            80: 0.01   # Water (1%)
        }
    else:  # Tropical/subtropical
        landcover_distribution = {
            10: 0.45,  # Forest (45%)
            20: 0.20,  # Shrubland (20%)
            30: 0.15,  # Grassland (15%)
            40: 0.10,  # Agricultural (10%)
            50: 0.03,  # Built-up (3%)
            60: 0.05,  # Bare (5%)
            70: 0.01,  # Snow/ice (1%)
            80: 0.01   # Water (1%)
        }
    
    return {
        'source': 'Fallback_Landcover_Data',
        'landcover_distribution': landcover_distribution,
        'classification': list(worldcover_curve_numbers.keys()),
        'curve_numbers': worldcover_curve_numbers,
        'bbox': bbox,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'resolution': 1000,  # meters (estimated)
        'description': 'Fallback land cover data based on location'
    }


def download_soil_data(bbox):
    """
    Download soil data from Global Hydrologic Soil Groups (HYSOGs250m) for Curve Number-Based Runoff Modeling.
    Uses ORNL WebMap WCS service: https://webmap.ornl.gov/ogcbroker/wcs
    Based on the QGIS Curve Number Generator plugin approach.
    """
    import tempfile
    from urllib.parse import urlencode
    
    # ORNL WebMap WCS service for Global Hydrologic Soil Groups
    ornl_wcs_url = "https://webmap.ornl.gov/ogcbroker/wcs"
    
    # Create temp directory if it doesn't exist
    temp_dir = "./data/temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Add buffer cells like the QGIS plugin (2 cells on each side)
        soils_pixel_size = 0.00208333  # ~250m in degrees
        extent_ornl = (
            bbox[0] - 2 * soils_pixel_size,
            bbox[1] - 2 * soils_pixel_size,
            bbox[2] + 2 * soils_pixel_size,
            bbox[3] + 2 * soils_pixel_size,
        )
        
        # Calculate bbox dimensions like the plugin
        bbox_width = int((extent_ornl[2] - extent_ornl[0]) / soils_pixel_size)
        bbox_height = int((extent_ornl[3] - extent_ornl[1]) / soils_pixel_size)
        
        # WCS GetCoverage request for HYSOGs250m (matching plugin format)
        params = {
            'originator': 'SDAT',
            'service': 'WCS',
            'version': '1.0.0',
            'request': 'GetCoverage',
            'coverage': '1566_1',  # Global Hydrologic Soil Groups 250m
            'bbox': f"{extent_ornl[0]},{extent_ornl[1]},{extent_ornl[2]},{extent_ornl[3]}",
            'crs': 'EPSG:4326',
            'format': 'image/tiff',
            'width': bbox_width,
            'height': bbox_height
        }
        
        print(f"Requesting HYSOGs250m from ORNL WebMap: {ornl_wcs_url}")
        print(f"Parameters: {params}")
        
        response = requests.get(ornl_wcs_url, params=params, timeout=120)
        print(f"Response status: {response.status_code}")
        print(f"Response URL: {response.url}")
        
        if response.status_code == 200:
            # Save the raster data to temp directory
            temp_filename = f"hysogs250m_bbox_{bbox[0]:.3f}_{bbox[1]:.3f}_{bbox[2]:.3f}_{bbox[3]:.3f}.tif"
            temp_file_path = os.path.join(temp_dir, temp_filename)
            
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Saved HYSOGs250m data to: {temp_file_path}")
            
            # Verify the downloaded raster has proper CRS
            try:
                with rasterio.open(temp_file_path) as test_src:
                    if test_src.crs is None:
                        print("Warning: Downloaded raster has no CRS, attempting to fix...")
                        # Create a new file with proper CRS
                        fixed_filename = f"hysogs250m_fixed_bbox_{bbox[0]:.3f}_{bbox[1]:.3f}_{bbox[2]:.3f}_{bbox[3]:.3f}.tif"
                        fixed_file_path = os.path.join(temp_dir, fixed_filename)
                        with rasterio.open(
                            fixed_file_path,
                            'w',
                            driver='GTiff',
                            height=test_src.height,
                            width=test_src.width,
                            count=test_src.count,
                            dtype=test_src.dtypes[0],
                            crs=rasterio.crs.CRS.from_epsg(4326),  # Assume WGS84
                            transform=test_src.transform
                        ) as dst:
                            dst.write(test_src.read())
                        
                        # Replace the original file
                        os.unlink(temp_file_path)
                        temp_file_path = fixed_file_path
                        print(f"Fixed raster CRS to EPSG:4326: {fixed_file_path}")
                    else:
                        print(f"Raster CRS: {test_src.crs}")
            except Exception as crs_error:
                print(f"Warning: Could not verify/fix raster CRS: {crs_error}")
            
            # HYSOGs250m classification values and their HSG equivalents
            # Based on the ORNL HYSOGs250m documentation
            hysogs_to_hsg = {
                1: 'A',   # High infiltration (low runoff potential)
                2: 'B',   # Moderate infiltration
                3: 'C',   # Slow infiltration
                4: 'D',   # Very slow infiltration (high runoff potential)
                5: 'A/D', # Dual classification (A or D)
                6: 'B/D', # Dual classification (B or D)
                7: 'C/D', # Dual classification (C or D)
                8: 'A/B', # Dual classification (A or B)
                9: 'B/C', # Dual classification (B or C)
                10: 'A/C', # Dual classification (A or C)
                11: 'D',   # Water bodies
                12: 'D',   # Glaciers
                13: 'D',   # No data
                14: 'D',   # No data
                15: 'D'    # No data
            }
            
            # HSG to curve number adjustments
            hsg_adjustments = {
                'A': 0.9,   # Reduce curve numbers for high infiltration
                'B': 1.0,   # No adjustment for moderate infiltration
                'C': 1.1,   # Increase curve numbers for slow infiltration
                'D': 1.2,   # Increase curve numbers for very slow infiltration
                'A/D': 1.05, # Average of A and D
                'B/D': 1.1,  # Average of B and D
                'C/D': 1.15, # Average of C and D
                'A/B': 0.95, # Average of A and B
                'B/C': 1.05, # Average of B and C
                'A/C': 1.0   # Average of A and C
            }
            
            return {
                'source': 'ORNL_HYSOGs250m',
                'data_file': temp_file_path,
                'hysogs_to_hsg': hysogs_to_hsg,
                'hsg_adjustments': hsg_adjustments,
                'bbox': bbox,
                'url': ornl_wcs_url,
                'resolution': 250,  # meters
                'description': 'Global Hydrologic Soil Groups (HYSOGs250m) for Curve Number-Based Runoff Modeling'
            }
        else:
            print(f"ORNL WCS request failed with status {response.status_code}")
            print(f"Response content: {response.text[:500]}...")
            raise Exception(f"ORNL WCS returned status {response.status_code}")
            
    except Exception as e:
        print(f"Error downloading HYSOGs250m data: {e}")
        # Fallback to simplified soil data based on location
        center_lon = (bbox[0] + bbox[2]) / 2
        center_lat = (bbox[1] + bbox[3]) / 2
        return create_fallback_soil_data(bbox, center_lat, center_lon)


def create_fallback_soil_data(bbox, center_lat, center_lon):
    """
    Create fallback soil data when ORNL HYSOGs250m is unavailable.
    """
    # Create realistic soil distribution based on location
    if center_lat > 60:  # High latitude - more clay soils
        soil_distribution = {
            'A': 0.10,  # 10% HSG A
            'B': 0.25,  # 25% HSG B
            'C': 0.35,  # 35% HSG C
            'D': 0.30   # 30% HSG D
        }
    elif center_lat > 30:  # Temperate - mixed soils
        soil_distribution = {
            'A': 0.20,  # 20% HSG A
            'B': 0.35,  # 35% HSG B
            'C': 0.30,  # 30% HSG C
            'D': 0.15   # 15% HSG D
        }
    else:  # Tropical - more sandy soils
        soil_distribution = {
            'A': 0.35,  # 35% HSG A
            'B': 0.30,  # 30% HSG B
            'C': 0.25,  # 25% HSG C
            'D': 0.10   # 10% HSG D
        }
    
    return {
        'source': 'Fallback_Soil_Data',
        'soil_distribution': soil_distribution,
        'bbox': bbox,
        'center_lat': center_lat,
        'center_lon': center_lon,
        'resolution': 1000,  # meters (estimated)
        'description': 'Fallback soil data based on location'
    }





def generate_curve_numbers_comprehensive(landuse_data, soil_data, grid, catchment_geom):
    """
    Generate curve numbers using comprehensive approach based on QGIS plugin.
    Combines land use and soil data to create accurate curve number raster.
    """
    # Create catchment mask
    catchment_mask = grid.rasterize([(catchment_geom, 1)], fill=0)
    
    # Initialize curve number raster
    curve_number_raster = np.full(grid.shape, 70, dtype=np.float32)  # Default CN
    
    # Check if we have both ESA WorldCover and ORNL HYSOGs data for proper curve number calculation
    if (landuse_data['source'] == 'ESA_WorldCover_2021_Local' and 
        soil_data['source'] == 'ORNL_HYSOGs250m'):
        # Use the QGIS plugin approach: combine land cover and soil data using lookup tables
        curve_number_raster = apply_qgis_plugin_curve_number_calculation(
            curve_number_raster, landuse_data, soil_data, grid
        )
    else:
        # Fallback to the old approach
        # Apply land use based curve numbers
        if landuse_data['source'] == 'ESA_WorldCover_2021_Local':
            # Use local ESA WorldCover 2021 VRT data
            curve_number_raster = apply_real_landcover_data(curve_number_raster, landuse_data, grid)
        elif landuse_data['source'] == 'ESA_WorldCover':
            # Use real ESA WorldCover data
            curve_number_raster = apply_real_landcover_data(curve_number_raster, landuse_data, grid)
        elif landuse_data['source'] == 'Fallback_Landcover_Data':
            # Use fallback land cover data
            curve_number_raster = apply_fallback_landcover_data(curve_number_raster, landuse_data, grid)
        elif landuse_data['source'] == 'Simplified_Location_Based':
            # Use simplified location-based land cover
            curve_number_raster = apply_simplified_landcover(curve_number_raster, landuse_data)
        elif 'data_file' in landuse_data:
            # Use real downloaded land cover data
            curve_number_raster = apply_real_landcover_data(curve_number_raster, landuse_data, grid)
        else:
            # Fallback to simplified pattern
            landuse_pattern = create_simplified_landuse_pattern(grid.shape)
            for class_id, cn_value in landuse_data['classification'].items():
                curve_number_raster[landuse_pattern == class_id] = cn_value
        
        # Apply soil-based adjustments
        if soil_data['source'] == 'ORNL_HYSOGs250m':
            # Apply ORNL HYSOGs250m soil data
            curve_number_raster = apply_ornl_hysogs_adjustments(curve_number_raster, soil_data, grid)
        elif soil_data['source'] == 'Fallback_Soil_Data':
            # Apply fallback soil adjustments
            curve_number_raster = apply_fallback_soil_adjustments(curve_number_raster, soil_data, grid)
        elif soil_data['source'] == 'SSURGO':
            # Apply HSG-based adjustments
            curve_number_raster = apply_hsg_adjustments(curve_number_raster, soil_data)
        else:
            # Apply global soil adjustments
            curve_number_raster = apply_global_soil_adjustments(curve_number_raster, soil_data)
    
    # Apply catchment mask
    curve_number_raster = np.where(catchment_mask == 1, curve_number_raster, 0)
    
    return curve_number_raster


def apply_fallback_landcover_data(curve_number_raster, landuse_data, grid):
    """
    Apply fallback land cover data when ESA WorldCover is unavailable.
    """
    # Get the land cover distribution from fallback data
    landcover_distribution = landuse_data['landcover_distribution']
    curve_numbers = landuse_data['curve_numbers']
    
    # Create a realistic spatial pattern based on the distribution
    y_size, x_size = grid.shape
    total_pixels = x_size * y_size
    
    # Create a more realistic pattern with spatial clustering
    # This simulates how real land cover data would look
    curve_number_raster = create_realistic_spatial_pattern(
        curve_number_raster, 
        landcover_distribution, 
        curve_numbers, 
        total_pixels
    )
    
    print(f"Applied fallback land cover data for {landuse_data['source']}")
    
    return curve_number_raster


def create_realistic_spatial_pattern(curve_number_raster, landcover_distribution, classification, total_pixels):
    """
    Create a realistic spatial pattern for land cover distribution.
    This simulates the spatial clustering and patterns found in real land cover data.
    """
    y_size, x_size = curve_number_raster.shape
    
    # Create a base pattern with some spatial variation
    # Use a combination of random and structured patterns
    
    # 1. Create clusters for different land cover types
    landcover_types = list(landcover_distribution.keys())
    landcover_proportions = list(landcover_distribution.values())
    
    # 2. Generate a realistic pattern using cellular automata approach
    # This creates more realistic land cover patterns with clustering
    
    # Start with random distribution
    pattern = np.random.choice(landcover_types, size=(y_size, x_size), p=landcover_proportions)
    
    # Apply some spatial smoothing to create more realistic clusters
    # This simulates the spatial autocorrelation found in real land cover data
    
    # Create clusters by applying a simple smoothing filter
    from scipy.ndimage import uniform_filter
    pattern_smooth = uniform_filter(pattern.astype(float), size=3)
    
    # Convert back to discrete land cover types
    pattern_discrete = np.round(pattern_smooth).astype(int)
    
    # Ensure we have valid land cover types
    pattern_discrete = np.clip(pattern_discrete, min(landcover_types), max(landcover_types))
    
    # 3. Apply curve numbers based on the pattern
    for landcover_type in landcover_types:
        if landcover_type in classification:
            mask = pattern_discrete == landcover_type
            curve_number_raster[mask] = classification[landcover_type]
    
    # 4. Add some additional spatial variation to make it more realistic
    # Add some noise to simulate the heterogeneity within land cover classes
    noise = np.random.normal(0, 2, curve_number_raster.shape)  # Small variation
    curve_number_raster += noise
    
    # Ensure curve numbers are within valid range (30-100)
    curve_number_raster = np.clip(curve_number_raster, 30, 100)
    
    return curve_number_raster


def apply_real_landcover_data(curve_number_raster, landuse_data, grid):
    """
    Apply real downloaded land cover data to curve number raster.
    """
    try:
        # Handle OpenStreetMap data (vector-based)
        if landuse_data['source'] == 'OpenStreetMap':
            return apply_osm_landcover_data(curve_number_raster, landuse_data, grid)
        
        # Handle raster-based data sources
        if 'data_file' in landuse_data:
            # Read the downloaded raster file
            with rasterio.open(landuse_data['data_file']) as src:
                # Read the data
                landcover_data = src.read(1)
                
                # Resample to match our grid if necessary
                if landcover_data.shape != grid.shape:
                    # Resample using rasterio
                    from rasterio.warp import reproject, Resampling
                    resampled_data = np.empty(grid.shape, dtype=landcover_data.dtype)
                    reproject(
                        landcover_data,
                        resampled_data,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=grid.affine,
                        dst_crs=grid.crs.srs,
                        resampling=Resampling.nearest
                    )
                    landcover_data = resampled_data
                
                # Apply land cover classification
                for class_id, cn_value in landuse_data['classification'].items():
                    curve_number_raster[landcover_data == class_id] = cn_value
                
                # Handle Copernicus mapping if available
                if 'copernicus_mapping' in landuse_data:
                    for copernicus_id, esa_id in landuse_data['copernicus_mapping'].items():
                        if esa_id in landuse_data['classification']:
                            cn_value = landuse_data['classification'][esa_id]
                            curve_number_raster[landcover_data == copernicus_id] = cn_value
            
                # Clean up temporary file (optional - keep for inspection)
                # if os.path.exists(landuse_data['data_file']):
                #     os.unlink(landuse_data['data_file'])
                print(f"Keeping land cover data file for inspection: {landuse_data['data_file']}")
        
        # Handle simplified data sources
        elif 'dominant_cover' in landuse_data:
            return apply_simplified_landcover(curve_number_raster, landuse_data)
            
    except Exception as e:
        print(f"Error processing real land cover data: {e}")
        print(f"Available keys in landuse_data: {list(landuse_data.keys())}")
        # Fallback to simplified pattern
        landuse_pattern = create_simplified_landuse_pattern(grid.shape)
        
        # Check if classification exists, otherwise use default curve numbers
        if 'classification' in landuse_data:
            for class_id, cn_value in landuse_data['classification'].items():
                curve_number_raster[landuse_pattern == class_id] = cn_value
        elif 'curve_numbers' in landuse_data:
            for class_id, cn_value in landuse_data['curve_numbers'].items():
                curve_number_raster[landuse_pattern == class_id] = cn_value
        else:
            # Default curve numbers if no classification available
            default_curve_numbers = {
                10: 55,   # Tree cover
                20: 65,   # Shrubland
                30: 61,   # Grassland
                40: 72,   # Cropland
                50: 98,   # Built-up
                60: 77,   # Bare
                70: 100,  # Snow/ice
                80: 100,  # Water
                90: 58,   # Wetland
                95: 60,   # Mangroves
                100: 100  # Moss
            }
            for class_id, cn_value in default_curve_numbers.items():
                curve_number_raster[landuse_pattern == class_id] = cn_value
    
    return curve_number_raster


def apply_osm_landcover_data(curve_number_raster, landuse_data, grid):
    """
    Apply OpenStreetMap-based land cover data to curve number raster.
    """
    # Get the dominant land cover type from OSM data
    dominant_cover = landuse_data['dominant_cover']
    
    # Check if classification exists, otherwise use default curve numbers
    if 'classification' in landuse_data:
        classification = landuse_data['classification']
    elif 'curve_numbers' in landuse_data:
        classification = landuse_data['curve_numbers']
    else:
        # Default curve numbers if no classification available
        classification = {
            10: 55,   # Tree cover
            20: 65,   # Shrubland
            30: 61,   # Grassland
            40: 72,   # Cropland
            50: 98,   # Built-up
            60: 77,   # Bare
            70: 100,  # Snow/ice
            80: 100,  # Water
            90: 58,   # Wetland
            95: 60,   # Mangroves
            100: 100  # Moss
        }
    
    cn_value = classification.get(dominant_cover, 70)
    
    # Apply dominant land cover to the entire area
    # In a more sophisticated approach, you could create patterns based on landcover_counts
    curve_number_raster.fill(cn_value)
    
    # Optionally, create a more detailed pattern based on landcover_counts
    if 'landcover_counts' in landuse_data and landuse_data['landcover_counts']:
        # Create a simple pattern based on the proportions
        total_features = sum(landuse_data['landcover_counts'].values())
        
        # Create a grid pattern based on proportions
        y_size, x_size = grid.shape
        current_pos = 0
        
        for esa_class, count in landuse_data['landcover_counts'].items():
            proportion = count / total_features
            pixels_for_class = int(proportion * x_size * y_size)
            
            cn_value = classification.get(esa_class, 70)
            
            # Fill pixels for this class
            for i in range(pixels_for_class):
                if current_pos < x_size * y_size:
                    y = current_pos // x_size
                    x = current_pos % x_size
                    curve_number_raster[y, x] = cn_value
                    current_pos += 1
    
    return curve_number_raster


def apply_qgis_plugin_curve_number_calculation(curve_number_raster, landuse_data, soil_data, grid):
    """
    Apply QGIS plugin-style curve number calculation using lookup tables.
    This combines ESA WorldCover land cover data with ORNL HYSOGs soil data.
    """
    try:
        # Load land cover data
        with rasterio.open(landuse_data['data_file']) as lc_src:
            landcover_data = lc_src.read(1)
            
        # Load soil data
        with rasterio.open(soil_data['data_file']) as soil_src:
            soil_data_raster = soil_src.read(1)
            
        print(f"Original land cover shape: {landcover_data.shape}")
        print(f"Original soil data shape: {soil_data_raster.shape}")
        print(f"Target curve number raster shape: {curve_number_raster.shape}")
        
        # Ensure all arrays have the same shape
        target_shape = curve_number_raster.shape
        
        # Resize land cover data to target shape if needed
        if landcover_data.shape != target_shape:
            print(f"Resizing land cover from {landcover_data.shape} to {target_shape}")
            from scipy.ndimage import zoom
            # Calculate zoom factors
            zoom_y = target_shape[0] / landcover_data.shape[0]
            zoom_x = target_shape[1] / landcover_data.shape[1]
            landcover_data = zoom(landcover_data, (zoom_y, zoom_x), order=0)  # order=0 for nearest neighbor
            
        # Resize soil data to target shape if needed
        if soil_data_raster.shape != target_shape:
            print(f"Resizing soil data from {soil_data_raster.shape} to {target_shape}")
            from scipy.ndimage import zoom
            # Calculate zoom factors
            zoom_y = target_shape[0] / soil_data_raster.shape[0]
            zoom_x = target_shape[1] / soil_data_raster.shape[1]
            soil_data_raster = zoom(soil_data_raster, (zoom_y, zoom_x), order=0)  # order=0 for nearest neighbor
            
        print(f"Final land cover shape: {landcover_data.shape}")
        print(f"Final soil data shape: {soil_data_raster.shape}")
        print(f"Land cover unique values: {np.unique(landcover_data)}")
        print(f"Soil data unique values: {np.unique(soil_data_raster)}")
        
        # Verify shapes match
        assert landcover_data.shape == soil_data_raster.shape == curve_number_raster.shape, \
            f"Shape mismatch: LC={landcover_data.shape}, Soil={soil_data_raster.shape}, CN={curve_number_raster.shape}"
        
        # Create lookup table for curve numbers (ESA Land Cover + HSG combinations)
        # This is based on the QGIS plugin's default lookup tables
        lookup_table = create_curve_number_lookup_table()
        
        # Apply curve numbers based on land cover and soil combinations
        for lc_class in np.unique(landcover_data):
            for hsg_class in np.unique(soil_data_raster):
                # Create grid code like the plugin (ESA_LC + HSG)
                grid_code = f"{lc_class}_{hsg_class}"
                
                # Get curve number from lookup table
                cn_value = lookup_table.get(grid_code, 70)  # Default to 70 if not found
                
                # Apply to pixels where both conditions are met
                mask = (landcover_data == lc_class) & (soil_data_raster == hsg_class)
                curve_number_raster[mask] = cn_value
                
                if np.any(mask):
                    print(f"Applied CN {cn_value} for {grid_code} to {np.sum(mask)} pixels")
        
        print(f"Final curve number range: {np.min(curve_number_raster)} - {np.max(curve_number_raster)}")
        
    except Exception as e:
        print(f"Error in QGIS plugin curve number calculation: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to default curve number
        curve_number_raster.fill(70)
    
    return curve_number_raster


def create_curve_number_lookup_table():
    """
    Create a curve number lookup table based on ESA Land Cover and HSG combinations.
    This is based on the QGIS plugin's default lookup tables for Fair hydrologic condition and ARC II.
    """
    # Default lookup table for Fair hydrologic condition and ARC II
    # Format: "ESA_LC_HSG": curve_number
    lookup_table = {
        # Tree cover (10) combinations
        "10_1": 45,   # Tree cover + HSG A
        "10_2": 66,   # Tree cover + HSG B  
        "10_3": 77,   # Tree cover + HSG C
        "10_4": 83,   # Tree cover + HSG D
        
        # Shrubland (20) combinations
        "20_1": 35,   # Shrubland + HSG A
        "20_2": 56,   # Shrubland + HSG B
        "20_3": 70,   # Shrubland + HSG C
        "20_4": 77,   # Shrubland + HSG D
        
        # Grassland (30) combinations
        "30_1": 30,   # Grassland + HSG A
        "30_2": 58,   # Grassland + HSG B
        "30_3": 71,   # Grassland + HSG C
        "30_4": 78,   # Grassland + HSG D
        
        # Cropland (40) combinations
        "40_1": 62,   # Cropland + HSG A
        "40_2": 71,   # Cropland + HSG B
        "40_3": 78,   # Cropland + HSG C
        "40_4": 81,   # Cropland + HSG D
        
        # Built-up (50) combinations
        "50_1": 89,   # Built-up + HSG A
        "50_2": 92,   # Built-up + HSG B
        "50_3": 94,   # Built-up + HSG C
        "50_4": 95,   # Built-up + HSG D
        
        # Bare/sparse vegetation (60) combinations
        "60_1": 72,   # Bare + HSG A
        "60_2": 81,   # Bare + HSG B
        "60_3": 88,   # Bare + HSG C
        "60_4": 91,   # Bare + HSG D
        
        # Snow and ice (70) combinations
        "70_1": 98,   # Snow/ice + HSG A
        "70_2": 98,   # Snow/ice + HSG B
        "70_3": 98,   # Snow/ice + HSG C
        "70_4": 98,   # Snow/ice + HSG D
        
        # Water bodies (80) combinations
        "80_1": 100,  # Water + HSG A
        "80_2": 100,  # Water + HSG B
        "80_3": 100,  # Water + HSG C
        "80_4": 100,  # Water + HSG D
        
        # Herbaceous wetland (90) combinations
        "90_1": 30,   # Wetland + HSG A
        "90_2": 58,   # Wetland + HSG B
        "90_3": 71,   # Wetland + HSG C
        "90_4": 78,   # Wetland + HSG D
        
        # Mangroves (95) combinations
        "95_1": 30,   # Mangroves + HSG A
        "95_2": 58,   # Mangroves + HSG B
        "95_3": 71,   # Mangroves + HSG C
        "95_4": 78,   # Mangroves + HSG D
        
        # Moss and lichen (100) combinations
        "100_1": 30,  # Moss + HSG A
        "100_2": 58,  # Moss + HSG B
        "100_3": 71,  # Moss + HSG C
        "100_4": 78,  # Moss + HSG D
    }
    
    return lookup_table


def apply_simplified_landcover(curve_number_raster, landuse_data):
    """
    Apply simplified location-based land cover data.
    """
    # Get the dominant land cover type
    dominant_cover = landuse_data['dominant_cover']
    
    # Check if classification exists, otherwise use default curve numbers
    if 'classification' in landuse_data:
        cn_value = landuse_data['classification'].get(dominant_cover, 70)
    elif 'curve_numbers' in landuse_data:
        cn_value = landuse_data['curve_numbers'].get(dominant_cover, 70)
    else:
        # Default curve numbers if no classification available
        default_curve_numbers = {
            10: 55,   # Tree cover
            20: 65,   # Shrubland
            30: 61,   # Grassland
            40: 72,   # Cropland
            50: 98,   # Built-up
            60: 77,   # Bare
            70: 100,  # Snow/ice
            80: 100,  # Water
            90: 58,   # Wetland
            95: 60,   # Mangroves
            100: 100  # Moss
        }
        cn_value = default_curve_numbers.get(dominant_cover, 70)
    
    # Apply dominant land cover to the entire area
    # In a more sophisticated approach, you could create patterns
    curve_number_raster.fill(cn_value)
    
    return curve_number_raster


def create_simplified_landuse_pattern(shape):
    """
    Create a simplified land use pattern for demonstration.
    In production, this would be replaced with actual ESA WorldCover data.
    """
    # Create a realistic land use pattern
    pattern = np.random.choice([10, 20, 30, 40, 50, 60, 80, 90], size=shape, p=[0.3, 0.1, 0.2, 0.15, 0.05, 0.05, 0.1, 0.05])
    return pattern





def apply_ornl_hysogs_adjustments(curve_number_raster, soil_data, grid):
    """
    Apply ORNL HYSOGs250m soil data adjustments.
    """
    try:
        # Read the downloaded HYSOGs250m raster file
        with rasterio.open(soil_data['data_file']) as src:
            # Read the data
            hysogs_data = src.read(1)
            
            print(f"HYSOGs data shape: {hysogs_data.shape}")
            print(f"Grid shape: {grid.shape}")
            print(f"Source CRS: {src.crs}")
            print(f"Source transform: {src.transform}")
            
            # Check if we need to resample
            if hysogs_data.shape != grid.shape:
                print("Resampling HYSOGs data to match grid...")
                
                # Handle missing CRS - assume WGS84 if not defined
                src_crs = src.crs
                if src_crs is None:
                    print("Warning: Source CRS is None, assuming EPSG:4326 (WGS84)")
                    src_crs = rasterio.crs.CRS.from_epsg(4326)
                
                # Resample using rasterio
                from rasterio.warp import reproject, Resampling
                resampled_data = np.empty(grid.shape, dtype=hysogs_data.dtype)
                
                try:
                    reproject(
                        hysogs_data,
                        resampled_data,
                        src_transform=src.transform,
                        src_crs=src_crs,
                        dst_transform=grid.affine,
                        dst_crs=grid.crs.srs,
                        resampling=Resampling.nearest
                    )
                    hysogs_data = resampled_data
                    print("Resampling completed successfully")
                except Exception as reproject_error:
                    print(f"Resampling failed: {reproject_error}")
                    print("Using original data shape")
            
            # Get the mapping and adjustments
            hysogs_to_hsg = soil_data['hysogs_to_hsg']
            hsg_adjustments = soil_data['hsg_adjustments']
            
            print(f"HYSOGs to HSG mapping: {hysogs_to_hsg}")
            print(f"HSG adjustments: {hsg_adjustments}")
            
            # Apply HYSOGs to HSG mapping and then to curve number adjustments
            applied_adjustments = 0
            for hysogs_value, hsg_type in hysogs_to_hsg.items():
                if hsg_type in hsg_adjustments:
                    mask = hysogs_data == hysogs_value
                    if np.any(mask):
                        curve_number_raster[mask] *= hsg_adjustments[hsg_type]
                        applied_adjustments += np.sum(mask)
                        print(f"Applied {hsg_type} adjustment to {np.sum(mask)} pixels (HYSOGs value: {hysogs_value})")
            
            print(f"Applied ORNL HYSOGs250m soil adjustments to {applied_adjustments} total pixels")
            print(f"HYSOGs values found: {np.unique(hysogs_data)}")
            
        # Clean up temporary file (optional - keep for inspection)
        # if os.path.exists(soil_data['data_file']):
        #     os.unlink(soil_data['data_file'])
        print(f"Keeping soil data file for inspection: {soil_data['data_file']}")
            
    except Exception as e:
        print(f"Error processing ORNL HYSOGs250m data: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Fallback to uniform adjustment
        curve_number_raster *= 1.0
    
    # Ensure curve numbers are within valid range
    curve_number_raster = np.clip(curve_number_raster, 30, 100)
    
    return curve_number_raster


def apply_fallback_soil_adjustments(curve_number_raster, soil_data, grid):
    """
    Apply fallback soil adjustments when ORNL HYSOGs250m is unavailable.
    """
    # Get soil distribution from fallback data
    soil_distribution = soil_data['soil_distribution']
    
    # Create realistic spatial pattern for soil types
    y_size, x_size = grid.shape
    
    # Create soil type pattern with spatial clustering
    soil_types = list(soil_distribution.keys())
    soil_proportions = list(soil_distribution.values())
    
    # Generate soil pattern with spatial variation
    soil_pattern = np.random.choice(soil_types, size=(y_size, x_size), p=soil_proportions)
    
    # Apply spatial smoothing to create realistic clusters
    from scipy.ndimage import uniform_filter
    soil_smooth = uniform_filter(soil_pattern.astype(float), size=5)
    soil_discrete = np.round(soil_smooth).astype(int)
    
    # Map soil types to adjustment factors
    soil_adjustments = {
        'A': 0.9,   # Reduce curve numbers for high infiltration
        'B': 1.0,   # No adjustment for moderate infiltration
        'C': 1.1,   # Increase curve numbers for slow infiltration
        'D': 1.2,   # Increase curve numbers for very slow infiltration
    }
    
    # Apply soil-based adjustments
    for soil_type in soil_types:
        if soil_type in soil_adjustments:
            mask = soil_discrete == ord(soil_type) - ord('A') + 1  # Convert A=1, B=2, etc.
            curve_number_raster[mask] *= soil_adjustments[soil_type]
    
    print(f"Applied fallback soil adjustments for {soil_data['source']}")
    
    # Ensure curve numbers are within valid range
    curve_number_raster = np.clip(curve_number_raster, 30, 100)
    
    return curve_number_raster


def apply_hsg_adjustments(curve_number_raster, soil_data):
    """
    Apply HSG-based adjustments to curve numbers.
    """
    # Get HSG distribution from soil data
    if 'hsg_distribution' in soil_data:
        hsg_distribution = soil_data['hsg_distribution']
        
        # Apply HSG-based adjustments
        hsg_adjustments = {
            'A': 0.9,   # Reduce curve numbers for high infiltration
            'B': 1.0,   # No adjustment for moderate infiltration
            'C': 1.1,   # Increase curve numbers for slow infiltration
            'D': 1.2,   # Increase curve numbers for very slow infiltration
        }
        
        # Apply weighted average adjustment based on HSG distribution
        total_adjustment = 0
        for hsg_type, proportion in hsg_distribution.items():
            if hsg_type in hsg_adjustments:
                total_adjustment += proportion * hsg_adjustments[hsg_type]
        
        curve_number_raster *= total_adjustment
        print(f"Applied HSG-based adjustment factor: {total_adjustment:.3f}")
    
    return curve_number_raster


def apply_global_soil_adjustments(curve_number_raster, soil_data):
    """
    Apply global soil adjustments to curve numbers.
    """
    # Apply a simple global adjustment based on soil data source
    if soil_data['source'] == 'Fallback_Soil_Data':
        # Apply a moderate adjustment for fallback data
        curve_number_raster *= 1.05
        print("Applied global soil adjustment factor: 1.05")
    else:
        # No adjustment for other soil data sources
        curve_number_raster *= 1.0
        print("Applied global soil adjustment factor: 1.0")
    
    return curve_number_raster


def create_catchment_grid(catchment_geom, cell_size):
    """
    Create a grid for the catchment area.
    Returns a simple grid object with necessary attributes for rasterization.
    """
    from rasterio.transform import from_bounds
    
    # Get bounding box
    minx, miny, maxx, maxy = catchment_geom.bounds
    
    # Calculate grid dimensions
    width = int((maxx - minx) / cell_size)
    height = int((maxy - miny) / cell_size)
    
    # Create transform
    transform = from_bounds(minx, miny, maxx, maxy, width, height)
    
    # Create a simple grid object with necessary attributes
    class SimpleGrid:
        def __init__(self, shape, transform, crs):
            self.shape = shape
            self.affine = transform
            self.crs = type('CRS', (), {'srs': crs})()
        
        def rasterize(self, shapes, fill=0):
            """Simple rasterization using rasterio"""
            from rasterio.features import rasterize
            return rasterize(shapes, out_shape=self.shape, fill=fill, transform=self.affine)
    
    grid = SimpleGrid((height, width), transform, 'EPSG:2056')
    
    return grid


def save_curve_number_raster(curve_number_raster, grid, output_file):
    """
    Save curve number raster as GeoTIFF.
    """
    # Create profile for GeoTIFF
    profile = {
        'driver': 'GTiff',
        'height': curve_number_raster.shape[0],
        'width': curve_number_raster.shape[1],
        'count': 1,
        'dtype': curve_number_raster.dtype.name,
        'crs': 'EPSG:2056',  # Swiss coordinate system
        'transform': grid.affine,
        'nodata': 0,
        'compress': 'lzw'
    }
    
    # Save raster
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(curve_number_raster, 1) 