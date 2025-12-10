import traceback
import builtins
import numpy as np
import os
from datetime import datetime
from calculations.curvenumbers import get_curve_numbers
from calculations.calculations import app
import json
from shapely import ops
from shapely.geometry import shape
import requests
import rasterio
from rasterio.features import rasterize
import pyproj

from calculations.discharge import construct_idf_curve, connect_prisma_with_retry

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

def parse_discharge_point(discharge_point, discharge_point_crs, transform=None, shape=None):
    """
    Parse discharge point coordinates and convert to raster coordinates.
    
    Args:
        discharge_point: Coordinates as tuple (x, y)
        discharge_point_crs: CRS string ("EPSG:4326", "EPSG:2056", or "raster")
        transform: Rasterio transform object (needed for coordinate conversion)
        shape: Raster shape (height, width) (needed for bounds checking)
    
    Returns:
        tuple: (row, col) raster coordinates or (None, None) if conversion failed
    """
    print(f"parse_discharge_point: input discharge_point coordinates: {discharge_point}")
    print(f"parse_discharge_point: input discharge_point_crs: {discharge_point_crs}")
    
    if discharge_point is None or len(discharge_point) != 2:
        return None, None
    
    x, y = discharge_point
    
    if discharge_point_crs == "raster":
        # Already in raster coordinates
        if shape is not None:
            row = max(0, min(int(x), shape[0] - 1))
            col = max(0, min(int(y), shape[1] - 1))
            return row, col
        else:
            return int(x), int(y)
    
    elif discharge_point_crs == "EPSG:4326":
        # Geographic coordinates (WGS84)
        if transform is not None and shape is not None:
            return geographic_to_raster_coords(x, y, transform, shape)
        else:
            print("Warning: Transform and shape needed for EPSG:4326 coordinate conversion")
            return None, None
    
    elif discharge_point_crs == "EPSG:2056":
        # Swiss coordinates
        if transform is not None and shape is not None:
            return geographic_to_raster_coords(x, y, transform, shape)
        else:
            print("Warning: Transform and shape needed for EPSG:2056 coordinate conversion")
            return None, None
    
    else:
        print(f"Warning: Unknown CRS: {discharge_point_crs}")
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
    water_balance_mode=None,  # Override water balance mode from database
    precipitation_factor=None,  # Override precipitation factor from database
    storm_center_mode=None,  # Override storm center mode from database
    routing_method=None,  # Override routing method from database
    readiness_to_drain=None,  # Readiness to drain parameter (negative values) to add to curve numbers
    discharge_point=None,  # Discharge point coordinates: (lon, lat) or (easting, northing) or (row, col)
    discharge_point_crs="EPSG:4326",  # CRS of discharge point: "EPSG:4326", "EPSG:2056", or "raster"
    project_easting=None,
    project_northing=None,
    cc_degree: float = 0.0,
    climate_scenario: str = "current",  # Climate scenario: "current", "1_5_degree", "2_degree", "3_degree", "4_degree"
    debug: bool = True,
):
    """
    NAM (Nedbør-Afstrømnings-Model) calculation based on distributed curve numbers and travel times.
    This is a distributed rainfall-runoff model that uses curve numbers for each cell and 
    calculates runoff at 10-minute timesteps using either travel time or isozone routing methods.
    """

    def _nam_print(*args, **kwargs):
        warning = kwargs.pop("warning", False)
        message = " ".join(str(arg) for arg in args) if args else ""
        message_lower = message.lower()
        if debug or warning or any(token in message_lower for token in ("warning", "error", "exception", "not found", "failed", "could not")):
            builtins.print(*args, **kwargs)

    print = _nam_print  # noqa: F841

    # Get NAM parameters from database only if not provided
    nam_obj = None
    if any(param is None for param in [water_balance_mode, precipitation_factor, storm_center_mode, routing_method]):
        from helpers.prisma import prisma
        nam_obj = prisma.nam.find_unique_or_raise(
            where={'id': nam_id},
            include={
                'WaterBalanceMode': True,
                'StormCenterMode': True,
                'RoutingMethod': True
            }
        )
        
        # Use database values for any None parameters
        water_balance_mode = water_balance_mode if water_balance_mode is not None else nam_obj.water_balance_mode
        precipitation_factor = precipitation_factor if precipitation_factor is not None else nam_obj.precipitation_factor
        storm_center_mode = storm_center_mode if storm_center_mode is not None else nam_obj.storm_center_mode
        routing_method = routing_method if routing_method is not None else nam_obj.routing_method
        readiness_to_drain = readiness_to_drain if readiness_to_drain is not None else nam_obj.readiness_to_drain
    
    print(f"NAM parameters:")
    print(f"  Water balance mode: {water_balance_mode}")
    print(f"  Precipitation factor: {precipitation_factor}")
    print(f"  Storm center mode: {storm_center_mode}")
    print(f"  Routing method: {routing_method}")
    print(f"  Readiness to drain: {readiness_to_drain}")
    
    # Add descriptions if we have the database object
    if nam_obj:
        print(f"  Water balance mode description: {nam_obj.WaterBalanceMode.description}")
        print(f"  Storm center mode description: {nam_obj.StormCenterMode.description}")
        print(f"  Routing method description: {nam_obj.RoutingMethod.description}")
    
    # Map climate scenario to cc_degree if not explicitly set
    scenario_to_degree = {
        "current": 0.0,
        "1_5_degree": 1.5,
        "2_degree": 2.0,
        "3_degree": 3.0
    }
    
    # Use climate_scenario to determine cc_degree
    if climate_scenario in scenario_to_degree:
        cc_degree = scenario_to_degree[climate_scenario]
    
    # Compute climate change factor if coordinates provided
    cc_factor = 0.0
    try:
        if project_easting is not None and project_northing is not None:
            from calculations.discharge import _project_to_wgs84, _load_cc_factor_simple    
            lon, lat = _project_to_wgs84(project_easting, project_northing)
            #cc_factor = _load_cc_factor(lon, lat, cc_degree)
            cc_factor = _load_cc_factor_simple(cc_degree)
    except Exception:
        cc_factor = 0.0

    intensity_fn = construct_idf_curve(
        P_low_1h,
        P_high_1h,
        P_low_24h,
        P_high_24h,
        rp_low,
        rp_high,
        cc_factor
    )
    
    # Initialize variables for distributed calculation
    cn_data = None
    isozone_data = None
    grid = None
    pixel_area_m2 = 25  # Default cell area [m²] (5x5 m)
    
    # 1. Load curve number raster and isozones raster
    if project_id and user_id:
        try:

            # Regenerate curve number raster and dem raster
            #get_curve_numbers(project_id, user_id)
            #extract_dem(project_id, user_id)
            #extract_dem_function = extract_dem.__wrapped__
        
            # Create kwargs dict to avoid argument conflicts
            #kwargs = {
            #    'projectId': project_id,
            #    'userId': user_id
            #}
            
            # Call the function without self parameter
            #result = extract_dem_function(**kwargs)

            # Resolve potential base directories for data
            base_dirs = []
            env_dir = os.getenv("DATA_DIR")
            if env_dir:
                base_dirs.append(env_dir)
            # Path relative to this file: src/api/calculations/ -> src/api/data
            base_dirs.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data')))
            # CWD fallback
            base_dirs.append(os.path.join(os.getcwd(), 'data'))

            # Load curve number raster
            curve_number_file = None
            for base in base_dirs:
                candidate = os.path.join(base, str(user_id), str(project_id), 'curvenumbers.tif')
                if os.path.exists(candidate):
                    curve_number_file = candidate
                    break
            if curve_number_file:
                print(f"Loading curve number raster from: {curve_number_file}")
                with rasterio.open(curve_number_file) as src:
                    cn_data = src.read(1)
                    cn_transform = src.transform
                    cn_crs = src.crs
                    pixel_area_m2 = abs(src.transform[0] * src.transform[4])  # Calculate actual pixel area
                    print(f"Curve number raster loaded, shape: {cn_data.shape}, pixel area: {pixel_area_m2:.2f} m²")
            else:
                tried = [os.path.join(b, str(user_id), str(project_id), 'curvenumbers.tif') for b in base_dirs]
                print("Curve number raster not found in any of:")
                for t in tried:
                    print(f"  - {t}")
                return {"error": "Curve number raster not found"}
            
            # Load isozones raster
            isozone_file = None
            for base in base_dirs:
                candidate = os.path.join(base, str(user_id), str(project_id), 'isozones_cog.tif')
                if os.path.exists(candidate):
                    isozone_file = candidate
                    break
            if isozone_file:
                print(f"Loading isozones raster from: {isozone_file}")
                with rasterio.open(isozone_file) as src:
                    isozone_data = src.read(1)
                    isozone_transform = src.transform
                    isozone_crs = src.crs
                    print(f"Isozones raster loaded, shape: {isozone_data.shape}, max zone: {int(np.nanmax(isozone_data))}")
            else:
                tried = [os.path.join(b, str(user_id), str(project_id), 'isozones_cog.tif') for b in base_dirs]
                print("Isozones raster not found in any of:")
                for t in tried:
                    print(f"  - {t}")
                return {"error": "Isozones raster not found"}
            
            # Load DEM data for elevation-based calculations
            dem_data = None
            dem_file = None
            for base in base_dirs:
                candidate = os.path.join(base, str(user_id), str(project_id), 'dem.tif')
                if os.path.exists(candidate):
                    dem_file = candidate
                    break
            if dem_file:
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
                print("Warning: DEM not available, will use simplified travel time calculation")
            
            # Load time_values.tif for time_values routing method
            time_values_data = None
            if routing_method == "time_values":
                time_values_file = os.path.join(base, str(user_id), str(project_id), 'time_values.tif')
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
    
    # Apply readiness to drain adjustment to curve numbers
    if readiness_to_drain is not None and readiness_to_drain != 0:
        print(f"Applying readiness to drain adjustment: {readiness_to_drain}")
        # Add readiness_to_drain value to each cell's curve number
        cn_data_adjusted = cn_data + readiness_to_drain
        print(f"Curve number adjustment applied: {readiness_to_drain}")
        print(f"  Original CN range: {np.nanmin(cn_data):.1f} - {np.nanmax(cn_data):.1f}")
        print(f"  Adjusted CN range: {np.nanmin(cn_data_adjusted):.1f} - {np.nanmax(cn_data_adjusted):.1f}")
        cn_data = cn_data_adjusted
    else:
        print(f"No readiness to drain adjustment (value: {readiness_to_drain})")
    
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
        cn_data = np.clip(cn_data, 30, 100)
        valid_mask = (cn_data > 0) & (cn_data <= 100)
    
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

    # ------------------------------------------------------------
    # 3. Calculate total storm precipitation for SCS method
    # ------------------------------------------------------------
    # We need the total precipitation for the entire storm duration

    # Raw IDF intensity for requested return period & climate scenario
    i_total = intensity_fn(rp_years=x, duration_minutes=Tc_total)  # [mm/h]
    I_event = float(i_total)
    duration_h = Tc_total / 60.0

    # Reference intensity for 100-year CURRENT climate (no cc_factor)
    try:
        i_100_ref = intensity_fn(rp_years=100, duration_minutes=Tc_total)
        I_ref_100 = float(i_100_ref)
    except Exception:
        # Fallback if 100a is outside the rp_low/rp_high range
        I_ref_100 = I_event

    # Soft limiter for extreme events:
    # - Do nothing up to 100a current climate (keeps calibration)
    # - For RP >= 300 OR any climate scenario above current,
    #   reduce the extra growth above 100a.
    k_extreme = 0.4  # 0 = no growth beyond 100a, 1 = full IDF; tune 0.3–0.5

    if ((x >= 300) or (x >= 100 and cc_degree > 0.0)) and (I_event > I_ref_100):
        I_eff = I_ref_100 + k_extreme * (I_event - I_ref_100)
        print(
            f"Extreme event adjustment: RP={x}, cc_degree={cc_degree}, "
            f"I_event={I_event:.1f} mm/h, I_ref_100={I_ref_100:.1f} mm/h, "
            f"I_eff={I_eff:.1f} mm/h (k_extreme={k_extreme:.2f})"
        )
    else:
        I_eff = I_event
        print(
            f"No extreme adjustment: RP={x}, cc_degree={cc_degree}, "
            f"I_event={I_event:.1f} mm/h, I_ref_100={I_ref_100:.1f} mm/h"
        )

    # Use effective intensity for the storm depth
    P_total_storm = I_eff * duration_h  # [mm]
    print(f"Total storm precipitation (effective): {P_total_storm:.2f} mm over {Tc_total} minutes")


    
    # Check if P_total_storm is sufficient to generate runoff
    mean_Ia = np.nanmean(Ia_cells[valid_mask])
    mean_S = np.nanmean(S_cells[valid_mask])
    if P_total_storm <= mean_Ia:
        print("WARNING: Total storm precipitation is less than mean initial abstraction!")
        print("This will result in zero runoff. Consider increasing return period or precipitation factor.")
    else:
        print(f"P_total_storm > Ia: {P_total_storm:.2f} > {mean_Ia:.2f} ✓")
    
    # Apply total precipitation to all cells at the beginning
    # This represents a single precipitation event at time t0
    P_total_storm = P_total_storm  # Total precipitation for the event [mm]
    
    print(f"Starting distributed NAM calculation with {max_timesteps} timesteps...")
    
    # Initialise storm stats (will be overwritten once storm_distribution is built)
    max_precip = float("nan")
    min_precip = float("nan")
    mean_precip = float("nan")

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
        center_row, center_col = parse_discharge_point(discharge_point, discharge_point_crs, cn_transform, cn_data.shape)
        
        if center_row is not None and center_col is not None:
            print(f"Storm center at user-provided coordinates: ({center_row}, {center_col})")
        else:
            # Fallback to centroid if no valid coordinates provided
            print("Warning: No valid user-provided coordinates, falling back to centroid")
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
    # Large stratiform storm
    # ------------------------------------------------------------
    # 3a. Storm geometry (same base behaviour as original)
    # ------------------------------------------------------------
    storm_radius_km = 4.0  # large stratiform storm

    # Get grid resolution in meters (EPSG:2056 coordinates)
    cell_size_m = abs(cn_transform.a)  # meters per pixel in x direction
    if cell_size_m <= 0:
        cell_size_m = 5.0  # fallback

    # Convert radius to pixels
    storm_radius_pixels = (storm_radius_km * 1000.0) / cell_size_m

    # Event intensity from IDF [mm/h] for this storm (already computed above)
    I_event = float(i_total)           # [mm/h]
    duration_h = Tc_total / 60.0       # [h]

    print(
        f"Storm parameters: radius={storm_radius_km:.1f}km "
        f"({storm_radius_pixels:.1f} px), cell_size={cell_size_m:.1f}m, "
        f"I_event={I_event:.1f} mm/h, duration={duration_h:.2f} h"
    )

    # ------------------------------------------------------------
    # 3b. Original exponential field (reference for mean)
    # ------------------------------------------------------------
    rows, cols = np.meshgrid(
        np.arange(cn_data.shape[0]),
        np.arange(cn_data.shape[1]),
        indexing="ij",
    )
    distances = np.sqrt((rows - center_row) ** 2 + (cols - center_col) ** 2)

    # Original behaviour: exponential decay from storm center
    base_kernel = np.exp(-distances / storm_radius_pixels)

    # This reproduces your old storm_distribution before we started tweaking:
    # storm_distribution_orig = P_total_storm * base_kernel
    storm_distribution = P_total_storm * base_kernel  # [mm]

    # Remember the original catchment-mean precipitation (so we don't change volume)
    original_mean_precip = float(np.mean(storm_distribution[valid_mask]))

    print(
        f"Original storm (reference): mean={original_mean_precip:.2f}mm, "
        f"max={float(np.max(storm_distribution[valid_mask])):.2f}mm"
    )

    # ------------------------------------------------------------
    # 3c. Intensity cap: trim unrealistic local peaks ONLY
    # ------------------------------------------------------------
    # Convert to local intensity [mm/h] using storm duration
    I_cells = storm_distribution / duration_h  # [mm/h]

    # Allow local intensities up to some factor of the design event intensity
    I_cap_factor = 1.2   # tune in 1.1–1.4 range; start with 1.2
    I_cap = I_cap_factor * I_event

    high_mask = (I_cells > I_cap) & valid_mask
    if np.any(high_mask):
        print(
            f"Intensity capping: {np.sum(high_mask)} cells exceed "
            f"{I_cap:.1f} mm/h ({I_cap_factor:.1f} × I_event)"
        )

        # Cap intensities
        I_cells[high_mask] = I_cap
        storm_distribution[high_mask] = I_cells[high_mask] * duration_h

        # After capping, renormalise to keep the SAME mean as original
        mean_after_cap = float(np.mean(storm_distribution[valid_mask]))
        if mean_after_cap > 0:
            scale_back = original_mean_precip / mean_afte

    
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
        
        P_mask = uniform_precip > Ia_cells[valid_mask]
        print(f"{np.sum(P_mask)} cells have P > Ia out of {np.sum(valid_mask)} valid cells")
        
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
            print(f"  Consider increasing precipitation_factor or return period.")
    elif water_balance_mode == "cumulative":
        # Cumulative approach: Use storm distribution with iterative water retention calculation
        # This approach considers the spatially varying storm and calculates retained water iteratively
        print(f"Cumulative approach - using storm distribution with iterative retention")
        
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
        P_mask = storm_distribution[valid_mask] > Ia_cells[valid_mask]
        print(f"{np.sum(P_mask)} cells have storm_distribution > Ia out of {np.sum(valid_mask)} valid cells")
        
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
            print(f"  Consider increasing precipitation_factor or return period.")
    # Calculate travel time for each cell
    # Determine discharge point coordinates (separate from storm center)
    discharge_row, discharge_col = parse_discharge_point(discharge_point, discharge_point_crs, cn_transform, cn_data.shape)
    
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
    else:
        print(f"Using discharge point: ({discharge_row}, {discharge_col})")
    
    # Calculate travel times using the best available method
    if dem_data is not None:
        print("Calculating travel times using overland flow method...")
        
        # Get discharge point elevation
        discharge_elevation = dem_data[discharge_row, discharge_col]
        print(f"Discharge point coordinates: ({discharge_row}, {discharge_col})")
        print(f"Discharge point elevation: {discharge_elevation:.1f} m")
        
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
                print(f"Error: No valid DEM cells found in catchment, using simplified approach")
                dem_data = None
        
        # Only proceed with overland flow if we have a valid discharge point
        if not np.isnan(discharge_elevation):
            # Calculate flow length and elevation difference for each cell
            rows, cols = np.meshgrid(np.arange(cn_data.shape[0]), np.arange(cn_data.shape[1]), indexing='ij')
            
            # Flow length: distance from each cell to discharge point [m]
            flow_lengths = np.sqrt((rows - discharge_row)**2 + (cols - discharge_col)**2) * np.sqrt(pixel_area_m2)
            
            # Elevation difference: elevation of each cell minus discharge elevation [m]
            elevation_diffs = dem_data - discharge_elevation
            
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
                
                # Use overland flow velocity based on slope
                # Typical overland flow velocities: 0.5-2.0 m/s depending on slope and surface
                velocities = 1.0 * np.sqrt(slope)  # [m/s] - conservative overland flow
                velocities = np.clip(velocities, 0.5, 2.0)  # [m/s] - realistic range
                
                # Convert to m/min for travel time calculation
                velocities_m_per_min = velocities * 60  # [m/min]
                
                # Calculate travel time: T = L / velocity [minutes]
                travel_times[valid_kirpich_mask] = L / velocities_m_per_min  # [minutes]
                
                print(f"Overland flow calculation completed:")
                print(f"  - Valid cells: {np.sum(valid_kirpich_mask)} out of {np.sum(valid_mask)}")
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
            else:
                print("Warning: No valid cells for overland flow calculation, using simplified approach")
                dem_data = None
        else:
            print("Warning: No valid discharge elevation, using simplified approach")
            dem_data = None
    
    if dem_data is None:
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
            print(f"  - Method: {'Overland Flow' if dem_data is not None else 'Simplified'}")
            if dem_data is None:
                print(f"  - Velocity: 60 m/min (1.0 m/s)")
        
    except Exception as e:
        print(f"Warning: Could not save routing results as TIFF: {e}")
    
    # Convert effective precipitation to runoff volume [m³] for each cell
    # Pe is in mm, convert to m³: Pe_mm * area_m² / 1000
    runoff_volumes = Pe_cells * pixel_area_m2 / 1000  # [m³]
    
    # Runoff volume summary
    print(f"Total effective precipitation: {np.sum(Pe_cells[valid_mask]):.2f}mm")
    print(f"Total runoff volume: {np.sum(runoff_volumes[valid_mask]):.2f}m³")
    print(f"Cells with runoff: {np.sum(runoff_volumes[valid_mask] > 0)} out of {np.sum(valid_mask)}")
    
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
        discharge = runoff_volume / (dt * 60)  # [m³/s]
        discharge_timesteps.append(discharge)
        if runoff_volume > 0:
            print(f"Timestep {i}: runoff_volume={runoff_volume:.3f} m³, Q={discharge:.3f} m³/s")
    
    # 4. Find maximum discharge (HQ)
    HQ = max(discharge_timesteps)
    max_timestep = discharge_timesteps.index(HQ)
    
    print(f"Maximum discharge: {HQ:.3f} m³/s at timestep {max_timestep}")
    print(f"Discharge time series: {[f'{q:.3f}' for q in discharge_timesteps]}")
    
    # Debug: Verify discharge_timesteps data and JSON serialization
    print(f"Debug - discharge_timesteps length: {len(discharge_timesteps)}")
    print(f"Debug - discharge_timesteps type: {type(discharge_timesteps)}")
    print(f"Debug - discharge_timesteps sample: {discharge_timesteps[:5] if len(discharge_timesteps) >= 5 else discharge_timesteps}")
    
    # Test JSON serialization
    try:
        # Convert numpy float32 values to regular Python floats for JSON serialization
        discharge_timesteps_serializable = [float(x) for x in discharge_timesteps]
        json_test = json.dumps(discharge_timesteps_serializable)
        print(f"Debug - JSON serialization successful, length: {len(json_test)}")
        print(f"Debug - JSON sample: {json_test[:100]}...")
    except Exception as e:
        print(f"Debug - JSON serialization failed: {e}")
    
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
        print(f"Method: {'Overland Flow' if dem_data is not None else 'Simplified'}")
        if dem_data is not None:
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
    prisma = None
    try:
        prisma = connect_prisma_with_retry()
        
        # Calculate average curve number for reporting
        effective_curve_number = np.nanmean(cn_data[valid_mask]) if cn_data is not None else curve_number

        # Debug: Prepare HQ_time data
        # Convert numpy float32 values to regular Python floats for JSON serialization
        discharge_timesteps_serializable = [float(x) for x in discharge_timesteps]
        hq_time_json = json.dumps(discharge_timesteps_serializable)
        print(f"Debug - HQ_time JSON length: {len(hq_time_json)}")
        print(f"Debug - HQ_time JSON sample: {hq_time_json[:200]}...")
        
        # Debug: Verify all data types
        print(f"Debug - HQ type: {type(HQ)}, value: {HQ}")
        print(f"Debug - Tc type: {type(Tc)}, value: {Tc}")
        print(f"Debug - TB type: {type(TB)}, value: {TB}")
        print(f"Debug - TFl type: {type(TFl)}, value: {TFl}")
        print(f"Debug - i_final type: {type(i_final)}, value: {i_final}")
        print(f"Debug - S type: {type(S)}, value: {S}")
        print(f"Debug - Ia type: {type(Ia)}, value: {Ia}")
        print(f"Debug - Pe_final type: {type(Pe_final)}, value: {Pe_final}")

        # Build the update data based on climate scenario
        result_data = {
            'HQ': float(HQ),
            'Tc': Tc,
            'TB': TB,
            'TFl': TFl,
            'i': float(i_final),
            'S': float(S),
            'Ia': float(Ia),
            'Pe': float(Pe_final),
            'HQ_time': hq_time_json,
        }
        
        # Use conditional logic to set the correct relation field
        if climate_scenario == "1_5_degree":
            data_update = {
                'NAM_Result_1_5': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "2_degree":
            data_update = {
                'NAM_Result_2': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "3_degree":
            data_update = {
                'NAM_Result_3': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        elif climate_scenario == "4_degree":
            data_update = {
                'NAM_Result_4': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        else:  # current
            data_update = {
                'NAM_Result': {
                    'upsert': {'update': result_data, 'create': result_data}
                }
            }
        
        updatedResults = prisma.nam.update(
            where={
                'id': nam_id
            },
            data=data_update
        )
        
        print(f"Debug - Database update successful: {updatedResults}")
    except Exception as e:
        print(f"Error updating NAM results: {e}")
        print(traceback.format_exc())
    finally:
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except Exception:
                pass
    print("NAM results updated in database.")
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
            "storm_radius": float(storm_radius_km),
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
    prisma = None
    try:
        prisma = connect_prisma_with_retry()
        project = prisma.project.find_unique_or_raise(
            where={
                'id': projectId
            }
        )
    finally:
        if prisma is not None:
            try:
                prisma.disconnect(5)
            except Exception:
                pass
    
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
        raise e
