import os
import time
from pysheds.grid import Grid
import fiona
import numpy as np
import json
import gc

def calculate_catchment(id, northing: float, easting: float):
    # Rertrieve and load DEM
    # ----------------------
    watershed = 'data/dir_3x3_3.tif'
    grid = Grid.from_raster(watershed)
    #accugrid = Grid.from_raster(accumulation)

    # Compute flow directions
    # -------------------------------------
    #dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    size = 10000
    #fdir = grid.read_raster(watershed, window=(pointx - 50000, pointy - 50000, pointx + 50000, pointy + 50000), window_crs=grid.crs)
    fdir = grid.read_raster(watershed, window=(round(northing - size,2), round(easting - size,2), round(northing + size,2), round(easting + size,2)), window_crs=grid.crs, dtype=np.uint8)
    
    grid.clip_to(fdir)
    """small_view = grid.view(fdir)
    raster = grid.to_raster(fdir, 'smallfdir.tif', target_view=small_view)

    del grid
    gc.collect()
    grid2 = Grid.from_raster('smallfdir.tif')
"""

    print(fdir.size)
    acc = grid.accumulation(fdir, dirmap=dirmap)
    x_snap, y_snap = grid.snap_to_mask(acc > 100, (northing, easting))

    # Delineate the catchment    
    catch = grid.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                        xytype='coordinate')
    # Crop and plot the catchment
    # ---------------------------
    # Clip the bounding box to the catchment
    grid.clip_to(catch)

    # Create view
    catch_view = grid.view(catch, dtype=np.uint8)

    # Create a vector representation of the catchment mask
    shapes = grid.polygonize(catch_view)

    # Specify schema
    schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    
    with fiona.open(f"data/temp/{id}.shp", 'w',
                    driver='Shapefile',
                    crs=grid.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL' : str(value)}
            rec['id'] = str(i)
            c.write(rec)
            i += 1

    return "OK"

# calculate_catchment(1,2593570,1175280.6)
# calculate_catchment(12, 2615928.7896,1185181.6449000016)
# calculate_catchment(13,2615870.2364000008,1185288.6799000017)
# calculate_catchment(15,2616096.171,1185144.9659999982)

i = 0
for feat in fiona.open("data/AUGUR_Testpunkte.shp"):
    print(i)
    print(feat['geometry']['coordinates'][0])
    print(feat['geometry']['coordinates'][1])
    
    calculate_catchment(i, feat['geometry']['coordinates'][0], feat['geometry']['coordinates'][1])
    i=i+1
