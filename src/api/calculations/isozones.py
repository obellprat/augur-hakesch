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
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rasterio.io import MemoryFile
from pysheds.view import View

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
    os.mkdir(f"data/temp/{self.request.id.__str__()}")
    
    # writing cloud optimized geotiff

    # Defining the output COG filename
    # path = data/NASADEM_HGT_n57e105_COG.tif
    cog_filename = f"data/temp/{self.request.id.__str__()}/isozones_cog.tif"

    src_profile = dict(
        driver="GTiff",
        dtype="int"
    )

    target_view = dist.viewfinder
    small_view2 = View.view(dist, target_view)

    height, width = small_view2.shape
    default_blockx = width
    default_profile = {
        'driver' : 'GTiff',
        'blockxsize' : 256,
        'blockysize' : 256,
        'count': 1
    }
    profile = default_profile
    profile_updates = {
        'crs' : dist.crs.srs,
        'transform' : dist.affine,
        'dtype' : dist.dtype.name,
        'nodata' : dist.nodata,
        'height' : height,
        'width' : width
    }
    profile.update(profile_updates)

    with MemoryFile() as memfile:
        # Opening an empty MemoryFile for in memory operation - faster
        with memfile.open(**profile) as mem:
            # Writing the array values to MemoryFile using the rasterio.io module
            # https://rasterio.readthedocs.io/en/stable/api/rasterio.io.html
            mem.write(np.asarray(dist), 1)

            dst_profile = cog_profiles.get("deflate")

            # Creating destination COG
            cog_translate(
                mem,
                cog_filename,
                dst_profile,
                use_cog_driver=True,
                in_memory=False
            )

    return