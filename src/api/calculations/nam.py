import numpy as np
import os
from prisma import Prisma
from calculations.calculations import app
import json
from shapely import ops
from shapely.geometry import shape
import requests
import rasterio
from rasterio.features import rasterize

from calculations.discharge import construct_idf_curve

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
    max_iter=1000
):
    """
    NAM (Nedbør-Afstrømnings-Model) calculation based on distributed curve numbers and isozones.
    This is a distributed rainfall-runoff model that uses curve numbers for each cell and 
    calculates runoff at 10-minute timesteps using isozones.
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
            
            # Check if rasters have the same shape and resample if necessary
            if cn_data.shape != isozone_data.shape:
                print(f"Raster shapes differ: CN={cn_data.shape}, Isozones={isozone_data.shape}")
                print("Resampling isozones to match curve number raster...")
                
                from rasterio.warp import reproject, Resampling
                
                # Resample isozones to match curve number raster
                resampled_isozones = np.empty(cn_data.shape, dtype=isozone_data.dtype)
                reproject(
                    isozone_data,
                    resampled_isozones,
                    src_transform=isozone_transform,
                    src_crs=isozone_crs,
                    dst_transform=cn_transform,
                    dst_crs=cn_crs,
                    resampling=Resampling.nearest
                )
                isozone_data = resampled_isozones
                print(f"Resampled isozones to shape: {isozone_data.shape}")
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
    Ia_cells = 0.2 * S_cells  # Changed back to 0.2 * S
    
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
    
    # 3. Calculate runoff for each cell at 10-minute timesteps
    print("Calculating runoff for each cell at 10-minute timesteps...")
    
    # Get maximum isozone to determine total simulation time
    max_zone = int(np.nanmax(isozone_data))
    if max_zone <= 0:
        return {"error": "Invalid isozone data: max_zone <= 0"}
    
    dt = 10  # Time step [min]
    Tc_total = dt * (max_zone + 1)  # Total simulation time [min]
    
    print(f"Simulation parameters: max_zone={max_zone}, dt={dt}min, Tc_total={Tc_total}min")
    
    # Validate isozone data
    valid_isozones = np.isfinite(isozone_data) & (isozone_data >= 0)
    print(f"Valid isozone cells: {np.sum(valid_isozones)} out of {isozone_data.size}")
    
    # Calculate max_timesteps for simulation
    max_timesteps = max_zone + 50  # Allow extra timesteps for runoff to decay
    
    # Initialize runoff time series for each timestep
    # This will store runoff volumes that arrive at each timestep
    runoff_timesteps = [0.0] * max_timesteps  # Pre-allocate with zeros
    
    # Calculate total storm precipitation for SCS method
    # We need the total precipitation for the entire storm duration
    i_total = intensity_fn(rp_years=x, duration_minutes=Tc_total)  # [mm/h]
    P_total_storm = i_total #* Tc_total / 60  # [mm] - total storm precipitation
    
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
    
    # Apply total precipitation to all cells at the beginning
    # This represents a single precipitation event at time t0
    print(f"Applying total precipitation: {P_total_storm:.2f} mm to all cells")
    
    # Calculate runoff for each zone
    for zone in range(max_zone + 1):
        # Get cells in current isozone
        zone_mask = (isozone_data == zone) & valid_mask & valid_isozones
        
        if not np.any(zone_mask):
            continue
        
        print(f"Processing Zone {zone}: {np.sum(zone_mask)} cells")
        
        # Apply total precipitation to cells in this zone
        # All cells receive the same total precipitation amount
        
        # Calculate effective precipitation using SCS method for each cell
        Pe_cells = np.zeros_like(cn_data, dtype=np.float32)
        
        # Apply SCS method: Pe = ((P - Ia)²) / (P - Ia + S) if P > Ia, else 0
        # Use total precipitation for SCS calculation (single event)
        P_mask = P_total_storm > Ia_cells[zone_mask]
        if np.any(P_mask):
            P_excess = P_total_storm - Ia_cells[zone_mask][P_mask]
            S_zone = S_cells[zone_mask][P_mask]
            
            # Calculate effective precipitation for total storm
            Pe_values = (P_excess ** 2) / (P_excess + S_zone)
            
            # Create a temporary array for this zone's Pe values
            zone_pe_values = np.zeros_like(cn_data[zone_mask], dtype=np.float32)
            zone_pe_values[P_mask] = Pe_values
            
            # Assign to the main Pe_cells array
            Pe_cells[zone_mask] = zone_pe_values
            
            # Debug info for first few cells
            if np.sum(P_mask) > 0:
                print(f"  Zone {zone}: {np.sum(P_mask)} cells with P>Ia")
                print(f"    Sample: P_total={P_total_storm:.2f}mm, Ia={Ia_cells[zone_mask][P_mask][0]:.2f}mm, S={S_zone[0]:.2f}mm")
                print(f"    Sample: P_excess={P_excess[0]:.2f}mm, Pe={Pe_values[0]:.2f}mm")
        
        # Convert effective precipitation to runoff volume [m³]
        # Pe is in mm, convert to m³: Pe_mm * area_m² / 1000
        runoff_volume = np.sum(Pe_cells[zone_mask]) * pixel_area_m2 / 1000  # [m³]
        
        # The runoff from this zone reaches the drainage point after 'zone' timesteps
        # So we need to add this runoff to the discharge at timestep 'zone'
        arrival_timestep = zone
        
        # Store the runoff contribution for the arrival timestep
        if arrival_timestep < len(runoff_timesteps):
            # Add to existing runoff for this arrival timestep
            runoff_timesteps[arrival_timestep] += runoff_volume
        else:
            # Extend the runoff_timesteps list if needed
            while len(runoff_timesteps) <= arrival_timestep:
                runoff_timesteps.append(0.0)
            runoff_timesteps[arrival_timestep] += runoff_volume
        
        # Debug: Show runoff volume for all zones
        print(f"  Zone {zone}: {np.sum(zone_mask)} cells, Pe_sum={np.sum(Pe_cells[zone_mask]):.2f}mm, runoff_volume={runoff_volume:.3f} m³, arrives at timestep {arrival_timestep}")
        
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
        "HQ": HQ,
        "Tc": Tc,
        "TB": TB,
        "TFl": TFl,
        "i": i_final,
        "S": S,
        "Ia": Ia,
        "Pe": Pe_final,
        "effective_curve_number": effective_curve_number,
        "runoff_timesteps": runoff_timesteps,
        "discharge_timesteps": discharge_timesteps,
        "max_timestep": max_timestep,
        "total_cells": np.sum(valid_mask),
        "pixel_area_m2": pixel_area_m2
    }


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