from pysheds.grid import Grid
import numpy as np
import rasterio
import gc
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rasterio.io import MemoryFile
from pysheds.view import Raster,View
from scipy.ndimage import gaussian_filter
import geopandas as gpd
from shapely import geometry, ops
import pandas as pd

from calculations.calculations import app

@app.task(name="calculate_isozones", bind=True)
def calculate_isozones(self, projectId: str, northing: float, easting: float):
    # Definitions

    v_gerinne = 1.5 # m/s
    cell_size = 5

    # Rertrieve and load DEM
    # ----------------------

    dem = 'data/geotiffminusriver.tif'
    grid = Grid.from_raster(dem)
        
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    self.update_state(state='PROGRESS',
                meta={'text': 'Reading DEM'})

    dem = grid.read_raster(dem, window=(northing - 10000, easting - 10000, northing + 10000, easting + 10000), window_crs=grid.crs)
    grid.clip_to(dem)
    small_view = grid.view(dem)
    grid.to_raster(dem, 'data/temp/smallfdir.tif', target_view=small_view)

    del grid
    gc.collect()
    grid2 = Grid.from_raster('data/temp/smallfdir.tif')
        
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions'})
    # calculate accumulation

    pit_filled_dem = grid2.fill_pits(dem)
    flooded_dem = grid2.fill_depressions(pit_filled_dem)
    inflated_dem = grid2.resolve_flats(flooded_dem)
    fdir = grid2.flowdir(inflated_dem, dirmap=dirmap)    
    
    acc = grid2.accumulation(fdir, dirmap=dirmap)
    x_snap, y_snap = grid2.snap_to_mask(acc > 10000, (northing, easting))

    
    self.update_state(state='PROGRESS',
                meta={'text': 'Delineate the catchment'})
    # Delineate the catchment    
    catch = grid2.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                        xytype='coordinate')
    # Crop and plot the catchment
    # ---------------------------
    # Clip the bounding box to the catchment
    grid2.clip_to(catch)


    # calculate slope
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculating slope'})
    slope = grid2.cell_slopes(fdir=fdir, dirmap=dirmap, dem=dem, nodata=0)
    #slope_percentage = gaussian_filter(slope, sigma=1)
    slope_percentage = slope * 100


    # create wald raster
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Getting forest'})
    forests = gpd.read_file('data/ch_wald.shp')
    grid2.clip_to(catch)
    # Convert catchment raster to vector geometry and find intersection
    shapes = grid2.polygonize()

    objektart = 'objektart'
    catchment_polygon = ops.unary_union([geometry.shape(shape)
                                        for shape, value in shapes])
    forests = forests[forests.intersects(catchment_polygon)]
    catchment_forests = gpd.GeoDataFrame(forests, 
                                    geometry=forests.intersection(catchment_polygon))

    # Convert forest to simple integer values
    forest_types = np.unique(catchment_forests[objektart])
    forest_types = pd.Series(np.arange(forest_types.size), index=forest_types)
    catchment_forests[objektart] = catchment_forests[objektart].map(forest_types)
    forests_polygons = zip(catchment_forests.geometry.values, catchment_forests[objektart].values)
    forests_raster = grid2.rasterize(forests_polygons, fill=-1)
    forests_raster[forests_raster >= 0] = 1
    forests_raster[forests_raster < 0] = 0

    # calculate "Hindernislayer".
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculating obstacle layer'})
    acc_view = grid2.view(acc)
    obstacle_grid = acc_view.copy()
    
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage < 1,slope_percentage>-100), forests_raster==1), 300,obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage < 1,slope_percentage>-100), forests_raster==0), 1500,obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 1,slope_percentage<5), forests_raster==1), 1500, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 1,slope_percentage<5), forests_raster==0), 750, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 5,slope_percentage<10), forests_raster==1), 750, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 5,slope_percentage<10), forests_raster==0), 375, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 10,slope_percentage<20), forests_raster==1), 500, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 10,slope_percentage<20), forests_raster==0), 250, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 20,slope_percentage<40), forests_raster==1), 375, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(np.logical_and(slope_percentage >= 20,slope_percentage<40), forests_raster==0), 188, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(slope_percentage >= 40, forests_raster==1), 300, obstacle_grid)
    obstacle_grid = np.where(np.logical_and(slope_percentage >= 40, forests_raster==0), 150, obstacle_grid)
    obstacle_grid = np.where(acc_view>10000, 100, obstacle_grid)

    obstacle_raster = Raster(obstacle_grid, viewfinder=grid2.viewfinder)

    # calculate raster distance
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculate distance'})
    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap, weights=obstacle_raster)

    #dist = dist * cell_size
    dist[dist == np.inf] = -1000000
    dist[dist <= 0] = -1000000
    dist = np.rint(((dist)/(v_gerinne * 60 * 100)) / 10) + 1  # strecke / geschwindigkeit * 60(-> für m/min) * 100 (hindernislayer) / 10 (-> 10 Minuten klassen) +1 da wir bei Klasse 1 starten

    dist[dist<=0] = None


    # writing cloud optimized geotiff
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Writing isozone file'})
    # Defining the output COG filename
    cog_filename = f"data/temp/isozones_cog.tif"

    src_profile = dict(
        driver="GTiff",
        dtype="int"
    )

    target_view = dist.viewfinder
    small_view2 = View.view(dist, target_view)

    height, width = small_view2.shape
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
        'nodata' : 0,
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
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Finish'})
    return