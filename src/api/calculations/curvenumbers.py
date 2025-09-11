"""
Curve Number Calculation Module

This module contains functions for calculating curve numbers using the QGIS approach
with local ESA WorldCover and either local HYSOGs or BEK (Bodeneignungskarte) data sources.

The module supports two soil data sources:
- HYSOGs: Global Hydrologic Soil Groups (HYSOGs250m) raster data
- BEK: Swiss soil suitability map (Bodeneignungskarte) shapefile data

When using BEK data, the module automatically falls back to HYSOGs for areas
where BEK data is not available or insufficient.
"""

import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import rasterio.windows
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely import ops
from prisma import Prisma
from calculations.calculations import app

@app.task(name="get_curve_numbers", bind=True)
def get_curve_numbers(self, projectId: str, userId: int, soil_data_source: str = "bek"):
    """
    Get curve numbers for a catchment geojson and save as raster.
    Uses local ESA WorldCover and either local HYSOGs or BEK (Bodeneignungskarte) data.
    Based on QGIS Curve Number Generator plugin approach.
    
    Args:
        projectId: Project ID
        userId: User ID  
        soil_data_source: "hysogs" for HYSOGs250m data or "bek" for BEK shapefile data
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
                meta={'text': 'Loading local data', 'progress': 20})
    
    # Convert bbox from EPSG:2056 to EPSG:4326 (WGS84) for data access
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
    
    # Load local ESA WorldCover data (no temp files)
    landuse_data = load_local_esa_worldcover(bbox_wgs84)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Loading soil data', 'progress': 40})
    
    # Load soil data based on source parameter
    if soil_data_source == "bek":
        soil_data = load_bek_soil_data(bbox_wgs84)
        # If BEK data is empty or insufficient, fallback to HYSOGs
        if soil_data['bek_data'] is None or soil_data['bek_data'].empty:
            print("BEK data not available or empty, falling back to HYSOGs")
            soil_data = load_local_hysogs_soil_data(bbox_wgs84)
    else:  # default to hysogs
        soil_data = load_local_hysogs_soil_data(bbox_wgs84)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Processing curve number data', 'progress': 60})
    
    # Create a grid for the catchment area
    cell_size = 5  # meters (ESA WorldCover resolution)
    # For EPSG:2056 (Swiss coordinates), cell_size is already in meters
    grid = create_catchment_grid(catchment_union, cell_size)
    
    # Generate curve numbers using QGIS approach only
    curve_number_raster = generate_curve_numbers_qgis_only(
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


def load_local_esa_worldcover(bbox):
    """
    Load land cover data from local ESA WorldCover 2021 VRT file.
    Simplified version that doesn't create temporary files.
    Uses the esa_worldcover_2021.vrt file in ./data.
    Based on the QGIS Curve Number Generator plugin approach.
    """
    import os
    
    # Local ESA WorldCover 2021 VRT file
    vrt_file_path = "./data/esa_worldcover_2021.vrt"
    
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
            
            print(f"Successfully loaded ESA WorldCover 2021 data for bbox: {bbox}")
            print(f"Data shape: {data.shape}")
            print(f"Unique values: {np.unique(data)}")
            
            return {
                'source': 'ESA_WorldCover_2021_Local',
                'data': data,
                'transform': window_transform,
                'crs': src.crs,
                'classification': worldcover_classes,
                'bbox': bbox,
                'vrt_file': vrt_file_path,
                'resolution': 10,  # meters
                'description': 'ESA WorldCover 2021 10m Global Land Cover (Local VRT)'
            }
            
    except Exception as e:
        print(f"Error reading ESA WorldCover 2021 VRT file: {e}")


def load_local_hysogs_soil_data(bbox):
    """
    Load soil data from local Global Hydrologic Soil Groups (HYSOGs250m) GeoTIFF.
    Simplified version that doesn't create temporary files.
    The local dataset is expected at `./data/HYSOGs250m.tif` in EPSG:4326.
    """
    # Path to local HYSOGs250m GeoTIFF
    local_tif_path = "./data/HYSOGs250m.tif"
    
    if not os.path.exists(local_tif_path):
        raise FileNotFoundError(f"Local HYSOGs250m GeoTIFF not found at {local_tif_path}")
    
    # Add buffer cells like the QGIS plugin (2 cells on each side)
    soils_pixel_size = 0.00208333  # ~250m in degrees
    extent_local = (
        bbox[0] - 2 * soils_pixel_size,
        bbox[1] - 2 * soils_pixel_size,
        bbox[2] + 2 * soils_pixel_size,
        bbox[3] + 2 * soils_pixel_size,
    )
    
    with rasterio.open(local_tif_path) as src:
        # Verify CRS
        src_crs = src.crs
        if src_crs is None:
            raise ValueError("Local HYSOGs250m GeoTIFF has no CRS; expected EPSG:4326")
        if str(src_crs).upper() not in ("EPSG:4326", "WGS84") and src_crs.to_epsg() != 4326:
            raise ValueError(f"Local HYSOGs250m GeoTIFF CRS is {src_crs}, expected EPSG:4326")
        
        # Compute window for the requested bounds
        window = rasterio.windows.from_bounds(
            extent_local[0], extent_local[1], extent_local[2], extent_local[3],
            src.transform
        )
        
        # Clamp window to dataset bounds
        full_window = rasterio.windows.Window(0, 0, src.width, src.height)
        try:
            window = window.intersection(full_window)
        except Exception:
            # If intersection fails, fallback to full window
            window = full_window
        
        # Read data in the window
        data = src.read(1, window=window)
        window_transform = rasterio.windows.transform(window, src.transform)
        
    # HYSOGs250m classification values and their HSG equivalents
    hysogs_to_hsg = {
        1: 'A',
        2: 'B',
        3: 'C',
        4: 'D',
        5: 'A/D',
        6: 'B/D',
        7: 'C/D',
        8: 'A/B',
        9: 'B/C',
        10: 'A/C',
        11: 'D',
        12: 'D',
        13: 'D',
        14: 'D',
        15: 'D'
    }
    
    # HSG to curve number adjustments
    hsg_adjustments = {
        'A': 0.9,
        'B': 1.0,
        'C': 1.1,
        'D': 1.2,
        'A/D': 1.05,
        'B/D': 1.1,
        'C/D': 1.15,
        'A/B': 0.95,
        'B/C': 1.05,
        'A/C': 1.0
    }
    
    return {
        'source': 'ORNL_HYSOGs250m',  # Keep same source label for downstream logic
        'data': data,
        'transform': window_transform,
        'crs': src.crs,
        'hysogs_to_hsg': hysogs_to_hsg,
        'hsg_adjustments': hsg_adjustments,
        'bbox': bbox,
        'resolution': 250,
        'description': 'Global Hydrologic Soil Groups (HYSOGs250m) loaded from local GeoTIFF'
    }


def load_bek_soil_data(bbox):
    """
    Load soil data from BEK (Bodeneignungskarte) shapefile.
    The BEK shapefile is expected at `./data/bek.shp` with fields:
    - WASSERDURC: Wasserdurchlässigkeit code (2..6)
    - VERNASS: Vernässung code (1..4) 
    - GRUNDIGKEI: Gründigkeit code (2..6)
    """
    # Path to BEK shapefile
    bek_path = "./data/Bodeneignungskarte_LV95.shp"
    
    if not os.path.exists(bek_path):
        raise FileNotFoundError(f"BEK shapefile not found at {bek_path}")
    
    # Read BEK shapefile
    bek = gpd.read_file(bek_path)
    
    if bek.crs is None:
        raise ValueError("BEK shapefile has no CRS")
    
    # Convert bbox from WGS84 to BEK CRS if needed
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", str(bek.crs), always_xy=True)
    
    # Convert bbox corners from WGS84 to BEK CRS
    minx, miny = transformer.transform(bbox[0], bbox[1])
    maxx, maxy = transformer.transform(bbox[2], bbox[3])
    
    # Create bounding box geometry for filtering
    from shapely.geometry import box
    bbox_geom = box(minx, miny, maxx, maxy)
    
    # Filter BEK features that intersect with the bbox
    bek_filtered = bek[bek.geometry.intersects(bbox_geom)].copy()
    
    if bek_filtered.empty:
        print("Warning: No BEK features found in the specified bounding box")
        # Return empty data structure
        return {
            'source': 'BEK',
            'data': None,
            'transform': None,
            'crs': bek.crs,
            'bek_data': bek_filtered,
            'bbox': bbox,
            'description': 'BEK (Bodeneignungskarte) soil data - no features in bbox'
        }
    
    # Validate required fields
    required_fields = ['WASSERDURC', 'VERNASS', 'GRUNDIGKEI']
    missing_fields = [f for f in required_fields if f not in bek_filtered.columns]
    if missing_fields:
        raise ValueError(f"BEK shapefile missing required fields: {missing_fields}")
    
    # Convert fields to numeric, handling any non-numeric values
    for field in required_fields:
        bek_filtered[field] = pd.to_numeric(bek_filtered[field], errors='coerce').astype('Int64')
    
    # Calculate HSG for each polygon
    bek_filtered['HSG_undrained'] = bek_filtered.apply(
        lambda row: calculate_hsg_undrained(
            row['WASSERDURC'], row['VERNASS'], row['GRUNDIGKEI']
        ), axis=1
    )
    
    bek_filtered['HSG_drained'] = bek_filtered.apply(
        lambda row: calculate_hsg_drained(
            row['WASSERDURC'], row['VERNASS'], row['GRUNDIGKEI']
        ), axis=1
    )
    
    print(f"Successfully loaded BEK data: {len(bek_filtered)} features")
    print(f"HSG undrained distribution: {bek_filtered['HSG_undrained'].value_counts().to_dict()}")
    print(f"HSG drained distribution: {bek_filtered['HSG_drained'].value_counts().to_dict()}")
    
    return {
        'source': 'BEK',
        'data': None,  # Will be rasterized later
        'transform': None,  # Will be set during rasterization
        'crs': bek.crs,
        'bek_data': bek_filtered,
        'bbox': bbox,
        'description': 'BEK (Bodeneignungskarte) soil data loaded from shapefile'
    }


def calculate_hsg_undrained(wd, ver, gr):
    """
    Calculate HSG for undrained conditions from BEK codes.
    Based on the NEH (Niederschlag-Evapotranspiration-Hydrologie) rules.
    """
    # Normalize codes (handle None/NaN values)
    wd = None if pd.isna(wd) or wd <= 0 else int(wd)
    ver = None if pd.isna(ver) or ver <= 0 else int(ver)
    gr = None if pd.isna(gr) or gr <= 0 else int(gr)
    
    # Baseline HSG from Wasserdurchlässigkeit
    baseline_hsg = {6: "A", 5: "B", 4: "C", 3: "D", 2: "D"}.get(wd)
    
    if baseline_hsg is None:
        return None
    
    hsg = baseline_hsg
    
    # Apply Vernässung adjustments (undrained)
    if ver in (3, 4):
        hsg = "D"  # High waterlogging -> D
    elif ver == 2:
        hsg = degrade_hsg(hsg, 1)  # Moderate waterlogging -> degrade by 1 class
    
    # Apply Gründigkeit adjustments
    if gr == 2:
        hsg = degrade_hsg(hsg, 2)  # Shallow soil -> degrade by 2 classes
    elif gr == 3:
        hsg = degrade_hsg(hsg, 1)  # Moderately shallow -> degrade by 1 class
    
    return hsg


def calculate_hsg_drained(wd, ver, gr):
    """
    Calculate HSG for drained conditions from BEK codes.
    Similar to undrained but ignores Vernässung (waterlogging).
    """
    # Normalize codes (handle None/NaN values)
    wd = None if pd.isna(wd) or wd <= 0 else int(wd)
    ver = None if pd.isna(ver) or ver <= 0 else int(ver)
    gr = None if pd.isna(gr) or gr <= 0 else int(gr)
    
    # Baseline HSG from Wasserdurchlässigkeit
    baseline_hsg = {6: "A", 5: "B", 4: "C", 3: "D", 2: "D"}.get(wd)
    
    if baseline_hsg is None:
        return None
    
    hsg = baseline_hsg
    
    # Ignore Vernässung for drained conditions
    # Apply only Gründigkeit adjustments
    if gr == 2:
        hsg = degrade_hsg(hsg, 2)  # Shallow soil -> degrade by 2 classes
    elif gr == 3:
        hsg = degrade_hsg(hsg, 1)  # Moderately shallow -> degrade by 1 class
    
    return hsg


def degrade_hsg(hsg, steps):
    """
    Degrade HSG by the specified number of steps.
    A -> B -> C -> D (D stays D)
    """
    if hsg is None:
        return None
    
    hsg_order = ["A", "B", "C", "D"]
    try:
        current_index = hsg_order.index(hsg)
        new_index = min(len(hsg_order) - 1, current_index + max(0, steps))
        return hsg_order[new_index]
    except ValueError:
        return None


def generate_curve_numbers_qgis_only(landuse_data, soil_data, grid, catchment_geom):
    """
    Generate curve numbers using QGIS approach only.
    Combines local ESA WorldCover with either HYSOGs or BEK soil data.
    """
    # Create catchment mask
    catchment_mask = grid.rasterize([(catchment_geom, 1)], fill=0)
    
    # Initialize curve number raster
    curve_number_raster = np.full(grid.shape, 70, dtype=np.float32)  # Default CN
    
    # Use QGIS plugin approach: combine land cover and soil data using lookup tables
    if soil_data['source'] == 'BEK':
        curve_number_raster = apply_bek_curve_number_calculation(
            curve_number_raster, landuse_data, soil_data, grid
        )
    else:  # HYSOGs
        curve_number_raster = apply_qgis_plugin_curve_number_calculation_simplified(
            curve_number_raster, landuse_data, soil_data, grid
        )
    
    # Apply catchment mask
    curve_number_raster = np.where(catchment_mask == 1, curve_number_raster, 0)
    
    return curve_number_raster


def apply_bek_curve_number_calculation(curve_number_raster, landuse_data, soil_data, grid):
    """
    Apply BEK-based curve number calculation.
    Rasterizes BEK polygons with HSG values and combines with land cover data.
    """
    print("BEK Curve Number Calculation")
    try:
        # Get target grid properties
        target_shape = curve_number_raster.shape
        target_transform = grid.affine
        target_crs = 'EPSG:2056'  # Swiss coordinate system
        
        print(f"Target grid shape: {target_shape}")
        print(f"Target transform: {target_transform}")
        print(f"Target CRS: {target_crs}")
        
        # Reproject and resample land cover data to match target grid (in memory)
        landcover_reprojected = reproject_raster_data_to_target(
            landuse_data['data'], 
            landuse_data['transform'],
            landuse_data['crs'],
            target_shape, 
            target_transform, 
            target_crs
        )
        
        print(f"Reprojected land cover shape: {landcover_reprojected.shape}")
        print(f"Land cover unique values: {np.unique(landcover_reprojected)}")
        
        # Rasterize BEK HSG data to target grid
        bek_data = soil_data['bek_data']
        
        # Convert BEK CRS to target CRS if needed
        if str(bek_data.crs) != target_crs:
            bek_data = bek_data.to_crs(target_crs)
        
        # Rasterize undrained HSG (default mode)
        hsg_undrained_raster = rasterize_bek_hsg(
            bek_data, 'HSG_undrained', target_shape, target_transform
        )
        
        print(f"BEK HSG undrained unique values: {np.unique(hsg_undrained_raster)}")
        
        # Check if we need HYSOGs fallback for areas without BEK data
        unknown_mask = (hsg_undrained_raster == 0)
        if np.any(unknown_mask):
            print(f"Found {np.sum(unknown_mask)} pixels without BEK HSG data, applying HYSOGs fallback")
            hsg_undrained_raster = apply_hysogs_fallback(
                hsg_undrained_raster, unknown_mask, target_shape, target_transform
            )
        
        # Verify shapes match
        assert landcover_reprojected.shape == hsg_undrained_raster.shape == curve_number_raster.shape, \
            f"Shape mismatch: LC={landcover_reprojected.shape}, HSG={hsg_undrained_raster.shape}, CN={curve_number_raster.shape}"
        
        # Create lookup table for curve numbers (ESA Land Cover + HSG combinations)
        lookup_table = create_curve_number_lookup_table()
        
        # Apply curve numbers based on land cover and HSG combinations
        for lc_class in np.unique(landcover_reprojected):
            for hsg_code in np.unique(hsg_undrained_raster):
                if hsg_code == 0:  # Skip unknown HSG
                    continue
                
                # Convert HSG code to letter
                hsg_letter = {1: "A", 2: "B", 3: "C", 4: "D"}.get(hsg_code)
                if hsg_letter is None:
                    continue
                
                # Create grid code like the plugin (ESA_LC + HSG)
                grid_code = f"{lc_class}_{hsg_code}"
                
                # Get curve number from lookup table
                cn_value = lookup_table.get(grid_code, 70)  # Default to 70 if not found
                
                # Apply to pixels where both conditions are met
                mask = (landcover_reprojected == lc_class) & (hsg_undrained_raster == hsg_code)
                curve_number_raster[mask] = cn_value
                
                if np.any(mask):
                    print(f"Applied CN {cn_value} for {grid_code} ({lc_class} + HSG {hsg_letter}) to {np.sum(mask)} pixels")
        
        print(f"Final curve number range: {np.min(curve_number_raster)} - {np.max(curve_number_raster)}")
        
    except Exception as e:
        print(f"Error in BEK curve number calculation: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to default curve number
        curve_number_raster.fill(70)
    
    return curve_number_raster


def rasterize_bek_hsg(bek_data, hsg_field, target_shape, target_transform):
    """
    Rasterize BEK polygons with HSG values to target grid.
    """
    # Create shapes for rasterization
    shapes = []
    for _, row in bek_data.iterrows():
        hsg = row[hsg_field]
        if hsg in ("A", "B", "C", "D") and row.geometry is not None and not row.geometry.is_empty:
            # Convert HSG letter to code
            hsg_code = {"A": 1, "B": 2, "C": 3, "D": 4}[hsg]
            shapes.append((row.geometry, hsg_code))
    
    if not shapes:
        print("Warning: No valid HSG polygons found for rasterization")
        return np.zeros(target_shape, dtype=np.uint8)
    
    # Rasterize
    hsg_raster = rasterize(
        shapes=shapes,
        out_shape=target_shape,
        transform=target_transform,
        fill=0,  # Unknown HSG = 0
        dtype=np.uint8,
        all_touched=True
    )
    
    return hsg_raster


def apply_hysogs_fallback(hsg_raster, unknown_mask, target_shape, target_transform):
    """
    Apply HYSOGs fallback for areas where BEK data is not available.
    """
    try:
        # Load HYSOGs data for the same area
        from pyproj import Transformer
        
        # Get bounds of the target grid
        from rasterio.transform import array_bounds
        minx, miny, maxx, maxy = array_bounds(target_shape[0], target_shape[1], target_transform)
        
        # Convert to WGS84 for HYSOGs loading
        transformer = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
        min_lon, min_lat = transformer.transform(minx, miny)
        max_lon, max_lat = transformer.transform(maxx, maxy)
        bbox_wgs84 = [min_lon, min_lat, max_lon, max_lat]
        
        # Load HYSOGs data
        hysogs_data = load_local_hysogs_soil_data(bbox_wgs84)
        
        # Reproject HYSOGs to target grid
        hysogs_reprojected = reproject_raster_data_to_target(
            hysogs_data['data'],
            hysogs_data['transform'],
            hysogs_data['crs'],
            target_shape,
            target_transform,
            'EPSG:2056'
        )
        
        # Convert HYSOGs codes to HSG codes
        hysogs_hsg_raster = np.zeros_like(hysogs_reprojected, dtype=np.uint8)
        for hysogs_code, hsg_letter in hysogs_data['hysogs_to_hsg'].items():
            if hsg_letter in ['A', 'B', 'C', 'D']:
                hsg_code = {'A': 1, 'B': 2, 'C': 3, 'D': 4}[hsg_letter]
                mask = (hysogs_reprojected == hysogs_code)
                hysogs_hsg_raster[mask] = hsg_code
        
        # Apply HYSOGs fallback only where BEK data is unknown
        hsg_raster[unknown_mask] = hysogs_hsg_raster[unknown_mask]
        
        print(f"Applied HYSOGs fallback to {np.sum(unknown_mask)} pixels")
        print(f"Final HSG distribution: {dict(zip(*np.unique(hsg_raster, return_counts=True)))}")
        
    except Exception as e:
        print(f"Error applying HYSOGs fallback: {e}")
        # Keep original raster if fallback fails
    
    return hsg_raster


def reproject_raster_data_to_target(data, source_transform, source_crs, target_shape, target_transform, target_crs):
    """
    Reproject and resample raster data to match the target grid specifications.
    Simplified version that works directly with data arrays without temp files.
    
    Args:
        data: Input raster data array
        source_transform: Source affine transform
        source_crs: Source coordinate reference system
        target_shape: Target shape (height, width)
        target_transform: Target affine transform
        target_crs: Target coordinate reference system
    
    Returns:
        numpy.ndarray: Reprojected raster data
    """
    from rasterio.warp import reproject, Resampling
    from rasterio.crs import CRS
    
    # Create target array
    target_data = np.empty(target_shape, dtype=data.dtype)
    
    # Use nearest neighbor resampling for categorical data
    resampling = Resampling.nearest
    
    # Reproject the data
    reproject(
        source=data,
        destination=target_data,
        src_transform=source_transform,
        src_crs=source_crs,
        dst_transform=target_transform,
        dst_crs=target_crs,
        resampling=resampling
    )
    
    return target_data


def apply_qgis_plugin_curve_number_calculation_simplified(curve_number_raster, landuse_data, soil_data, grid):
    """
    Apply QGIS plugin-style curve number calculation using lookup tables.
    Simplified version that works directly with data arrays without temp files.
    This combines ESA WorldCover land cover data with ORNL HYSOGs soil data.
    """
    print("QGIS Plugin Curve Number Calculation (Simplified)")
    try:
        # Get target grid properties
        target_shape = curve_number_raster.shape
        target_transform = grid.affine
        target_crs = 'EPSG:2056'  # Swiss coordinate system
        
        print(f"Target grid shape: {target_shape}")
        print(f"Target transform: {target_transform}")
        print(f"Target CRS: {target_crs}")
        
        # Reproject and resample land cover data to match target grid (in memory)
        landcover_reprojected = reproject_raster_data_to_target(
            landuse_data['data'], 
            landuse_data['transform'],
            landuse_data['crs'],
            target_shape, 
            target_transform, 
            target_crs
        )
        
        # Reproject and resample soil data to match target grid (in memory)
        soil_reprojected = reproject_raster_data_to_target(
            soil_data['data'], 
            soil_data['transform'],
            soil_data['crs'],
            target_shape, 
            target_transform, 
            target_crs
        )
        
        print(f"Reprojected land cover shape: {landcover_reprojected.shape}")
        print(f"Reprojected soil data shape: {soil_reprojected.shape}")
        print(f"Land cover unique values: {np.unique(landcover_reprojected)}")
        print(f"Soil data unique values: {np.unique(soil_reprojected)}")
        
        # Verify shapes match
        assert landcover_reprojected.shape == soil_reprojected.shape == curve_number_raster.shape, \
            f"Shape mismatch after reprojection: LC={landcover_reprojected.shape}, Soil={soil_reprojected.shape}, CN={curve_number_raster.shape}"
        
        # Create lookup table for curve numbers (ESA Land Cover + HSG combinations)
        # This is based on the QGIS plugin's default lookup tables
        lookup_table = create_curve_number_lookup_table()
        
        # Apply curve numbers based on land cover and soil combinations
        for lc_class in np.unique(landcover_reprojected):
            for hsg_class in np.unique(soil_reprojected):
                # Create grid code like the plugin (ESA_LC + HSG)
                grid_code = f"{lc_class}_{hsg_class}"
                
                # Get curve number from lookup table
                cn_value = lookup_table.get(grid_code, 70)  # Default to 70 if not found
                
                # Apply to pixels where both conditions are met
                mask = (landcover_reprojected == lc_class) & (soil_reprojected == hsg_class)
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
