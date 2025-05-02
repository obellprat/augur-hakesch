import os
from pysheds.grid import Grid
import numpy as np
import rasterio
import json
import gc
import zipfile
import io
import binascii
import shutil
from celery.utils.log import get_task_logger

from calculations.calculations import app

@app.task(name="calculate_isozones", bind=True)
def calculate_isozones(self, northing: float, easting: float):
    # Definitions

    v_gerinne = 1.5 # m/s
    v_oberflaeche = 0.5 # m/s
    cell_size = 5

    # Rertrieve and load DEM
    # ----------------------

    watershed = 'data/dir_3x3_3.tif'
    self.update_state(state='PROGRESS',
                meta={'text': 'Reading watershed'})
    grid = Grid.from_raster(watershed)
        
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions'})
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)

    fdir = grid.read_raster(watershed, window=(northing - 10000, easting - 10000, northing + 10000, easting + 10000), window_crs=grid.crs, dtype=np.uint8)
    
    grid.clip_to(fdir)
    small_view = grid.view(fdir)
    grid.to_raster(fdir, 'data/temp/smallfdir.tif', target_view=small_view)

    del grid
    gc.collect()
    grid2 = Grid.from_raster('data/temp/smallfdir.tif')

    self.update_state(state='PROGRESS',
                meta={'text': 'Calculation accumulation'})
    acc = grid2.accumulation(fdir, dirmap=dirmap)

    x_snap, y_snap = grid2.snap_to_mask(acc > 10000, (northing, easting))

    # Delineate the catchment    
    self.update_state(state='PROGRESS',
                meta={'text': 'Delineate the catchment'})
    catch = grid2.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                        xytype='coordinate')
    # Crop and plot the catchment
    # ---------------------------
    # Clip the bounding box to the catchment
    grid2.clip_to(catch)

    # calculate "Hindernislayer".
    obstacle_grid = acc.copy()
    obstacle_grid[acc >= 10000] = 1
    obstacle_grid[acc < 10000] = v_gerinne / v_oberflaeche


    self.update_state(state='PROGRESS', meta={'text': 'Calculate distance with velocity to outlet'})
    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap, weights=obstacle_grid)

    dist = dist * cell_size
    dist[dist == np.inf] = -1000
    dist = np.rint(((dist/v_gerinne) / 60) / 10)   # strecke / geschwindigkeit / 60(-> für m/min) / 10 (-> 10 Minuten klassen) 

    # write geotiff to tempdir
    os.mkdir(f"data/{self.request.id.__str__()}")
    
    grid2.to_raster(dist, f"data/{self.request.id.__str__()}/isozones.tif", target_view=small_view)

    return