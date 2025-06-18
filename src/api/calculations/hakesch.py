from pysheds.grid import Grid
import numpy as np
import gc
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rasterio.io import MemoryFile
from pysheds.view import Raster,View
from scipy.ndimage import gaussian_filter
import geopandas as gpd
from shapely import geometry, ops
import pandas as pd
import os
from prisma import Prisma
from calculations.calculations import app
import fiona
import json
from fiona.crs import CRS
from shapely.geometry import shape



from calculations.calculations import app

@app.task(name="modifizierte_fliesszeit", bind=True)
def modifizierte_fliesszeit(self, 
    P_low_1h,
    P_high_1h,
    P_low_24h,
    P_high_24h,
    rp_low,
    rp_high,  
    x:float,
    Vo20:int,           # Wetting volume for 20-year event [mm]
    L:float,              # Channel length up to the watershed ridge [m] 
    delta_H:float,        # Elevation difference along L [m]
    psi:float,            # Peak flow coefficient [-]
    E:float,              # Catchment area [km²]
    mod_fliesszeit_id:int, # db id for updating results
    TB_start=30,    # Initial value for TB [min]
    istep=5,        # Step size for TB [min]
    tol=5,          # Convergence tolerance [mm]
    max_iter=1000
):
    intensity_fn = construct_idf_curve(P_low_1h, P_high_1h, P_low_24h, P_high_24h, rp_low, rp_high)
    # 1. Wetting volume depending on x
    if x == 2.3:
        Vox = 0.5 * Vo20
    elif x == 100:
        Vox = 1.3 * Vo20
    elif x == 20:
        Vox = Vo20
    else:
        raise ValueError("Return period x must be 2.3, 20 or 100.")

    # 2. Flow time according to Kirpich
    J = delta_H / L
    TFl = 0.0195 * (L ** 0.77) * (J ** -0.385)

    # 3. Iteration to determine TB
    TB = TB_start
    for _ in range(max_iter):
        Tc = TB + TFl
        ix = intensity_fn(rp_years = x, duration_minutes = Tc)  # [mm/h]
        #print(f"Current TB: {TB}, Intensity: {ix}")
        #print(f"Vox: {Vox}, TFl: {TFl}, Tc: {Tc}")
        #print(f"criterion:{abs(TB / 60 * ix - Vox)}")
        if abs(TB / 60 * ix - Vox) < tol:
            # Convergence reached
            break 
        else: 
            if TB * ix < Vox:
                TB_new = TB - istep
            else:
                TB_new = TB + istep
            TB = TB_new
    else:
        raise RuntimeError("TB iteration did not converge.")

    Tc = TB + TFl
    i_final = intensity_fn(rp_years = x, duration_minutes = Tc)
    HQ = 0.278 * i_final * psi * E


    prisma = Prisma()
    prisma.connect()
    
    updatedResults = prisma.mod_fliesszeit_result.upsert(
        where = {
            'mod_fliesszeit' : mod_fliesszeit_id
        },
        data = {
            'update' : {
                'HQ' : HQ,
                'Tc' : Tc,
                'TB' : TB,
                'TFl' : TFl,
                'Vox' : Vox
            },
            'create' : {
                'HQ' : HQ,
                'Tc' : Tc,
                'TB' : TB,
                'i' : i_final,
                'TFl' : TFl,
                'Vox' : Vox,
                'mod_fliesszeit' : mod_fliesszeit_id
            }
        }
        
    )

    prisma.disconnect(5)

    return {
        "HQ": HQ,
        "Tc": Tc,
        "TB": TB,
        "TFl": TFl,
        "i": i_final,
        "Vox": Vox
    }


def construct_idf_curve(P_low_1h, P_high_1h, P_low_24h, P_high_24h, rp_low, rp_high2):
    
    """
    Constructs an IDF curve with user-defined lower and upper return periods.
    Inputs:
        P_low_1h:   Precipitation [mm] for lower return period, 1 hour duration
        P_high_1h:  Precipitation [mm] for upper return period, 1 hour duration
        P_low_24h:  Precipitation [mm] for lower return period, 24 hour duration
        P_high_24h: Precipitation [mm] for upper return period, 24 hour duration
        rp_low:     Lower return period (e.g. 2.33) as string
        rp_high:    Upper return period (e.g. 100) as string
    Returns:
        idf_intensity: function(duration_minutes, return_period_years) -> intensity [mm/h]
    """

    # Convert return periods from string to float
    log_rp = np.log10([rp_low, rp_high2])
    P_1h = [P_low_1h, P_high_1h]
    P_24h = [P_low_24h, P_high_24h]

    # Linear fit for 1h and 24h precipitation
    coeffs_1h = np.polyfit(log_rp, P_1h, 1)
    coeffs_24h = np.polyfit(log_rp, P_24h, 1)

    def precipitation_amount(duration_h, rp_years):
        log_rp_val = np.log10(rp_years)
        if duration_h == 1:
            return coeffs_1h[0] * log_rp_val + coeffs_1h[1]
        elif duration_h == 24:
            return coeffs_24h[0] * log_rp_val + coeffs_24h[1]
        else:
            raise ValueError("Only 1h and 24h durations supported for precipitation amount.")

    def idf_intensity(rp_years, duration_minutes):
        # Convert return periods from string to float
        duration_h = duration_minutes / 60.0
        P1 = precipitation_amount(1, rp_years)
        P24 = precipitation_amount(24, rp_years)
        I1 = P1 / 1.0
        I24 = P24 / 24.0
        log_durations = np.log10([1, 24])
        log_intensities = np.log10([I1, I24])
        slope, intercept = np.polyfit(log_durations, log_intensities, 1)
        log_duration = np.log10(duration_h)
        log_intensity = slope * log_duration + intercept
        return 10 ** log_intensity

    return idf_intensity

# Example usage:
# idf_fn = construct_idf_curve(25, 50, 60, 120, 2.33, 100)

@app.task(name="prepare_hakesch_hydroparameters", bind=True)
def prepare_hakesch_hydroparameters(self, projectId: str, userId: int, northing: float, easting: float, a_crit = 10000, v_gerinne = 1.5):
    # Definitions
    cell_size = 5

    # Rertrieve and load DEM
    # ----------------------

    dem = 'data/geotiffminusriver.tif'
    grid = Grid.from_raster(dem)
        
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    self.update_state(state='PROGRESS',
                meta={'text': 'Reading DEM', 'progress' : 5})

    dem = grid.read_raster(dem, window=(northing - 10000, easting - 10000, northing + 10000, easting + 10000), window_crs=grid.crs)
    grid.clip_to(dem)
    small_view = grid.view(dem)
    grid.to_raster(dem, 'data/temp/smallfdir.tif', target_view=small_view)

    del grid
    gc.collect()
    grid2 = Grid.from_raster('data/temp/smallfdir.tif')
        
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Fill pits', 'progress' : 8})
    

    # calculate accumulation

    pit_filled_dem = grid2.fill_pits(dem)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Fill depressions', 'progress' : 16})
    flooded_dem = grid2.fill_depressions(pit_filled_dem)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Resolve flats', 'progress' : 22})
    inflated_dem = grid2.resolve_flats(flooded_dem)
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions: Accumulation', 'progress' : 40})
    fdir = grid2.flowdir(inflated_dem, dirmap=dirmap)    
    
    acc = grid2.accumulation(fdir, dirmap=dirmap)

    
    self.update_state(state='PROGRESS',
                meta={'text': 'Delineate the catchment', 'progress' : 50})
    

    # Delineate the catchment
    x_snap, y_snap = grid2.snap_to_mask(acc > a_crit, (northing, easting))
    catch = grid2.catchment(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap, 
                        xytype='coordinate')

    # Clip the bounding box to the catchment
    grid2.clip_to(catch)

    # calculate catchment area
    num_cells = np.sum(catch)
    cell_area = cell_size ** 2
    catchment_area = num_cells * cell_area
    catchmentkm2 = catchment_area/(1000*1000)

    # Extract river network and calculate cumulative length
    branches = grid2.extract_river_network(fdir, acc > a_crit, dirmap=dirmap)
    L_cum = cumulative_length(branches)

    dem_view = grid2.view(dem)
    dem_view[dem_view < 0] = np.nan
    delta_H = float(np.nanmax(dem_view) - np.nanmin(dem_view)) 

    # calculate slope
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculating slope', 'progress' : 60})
    slope = grid2.cell_slopes(fdir=fdir, dirmap=dirmap, dem=dem, nodata=0)
    slope_percentage = slope * 100


    # create wald raster    
    self.update_state(state='PROGRESS',
                meta={'text': 'Getting forest', 'progress' : 70})
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
                meta={'text': 'Calculating obstacle layer', 'progress' : 80})
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

    # Compute maximum distance to outlet
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Calculate distance', 'progress' : 85})
    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap)  
    dist = dist * cell_size
    dist[dist == np.inf] = -1000000
    dist_max = np.nanmax(dist)

    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, xytype='coordinate', mask=grid2.mask, dirmap=dirmap, weights=obstacle_raster)

    #dist = dist * cell_size
    dist = dist * cell_size
    dist[dist == np.inf] = -1000000
    dist[dist <= 0] = -1000000
    dist = np.rint(((dist)/(v_gerinne * 60 * 100)) / 10) + 1  # strecke / geschwindigkeit * 60(-> für m/min) * 100 (hindernislayer) / 10 (-> 10 Minuten klassen) +1 da wir bei Klasse 1 starten

    dist[dist<=0] = None


    # writing cloud optimized geotiff
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Writing isozone file', 'progress' : 90})
    # Defining the output COG filename
    if not os.path.exists(f"data/{userId}"):
        os.makedirs(f"data/{userId}")

    if not os.path.exists(f"data/{userId}/{projectId}"):
        os.makedirs(f"data/{userId}/{projectId}")

    cog_filename = f"data/{userId}/{projectId}/isozones_cog.tif"

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
                meta={'text': 'Polygonize catchment', 'progress' : 92})
    # Create a vector representation of the catchment mask
    catch_view = grid2.view(catch, dtype=np.uint8)
    shapes = grid2.polygonize(catch_view)

    # Specify schema
    schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Creating geometry', 'progress' : 95})
    with fiona.open(f"data/{userId}/{projectId}/catchment.geojson", 'w',
                    driver='GeoJSON',
                    crs=grid2.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL' : str(value)}
            rec['id'] = str(i)
            c.write(rec)
            i += 1

    with open(f"data/{userId}/{projectId}/catchment.geojson", 'r') as file:
        data = json.load(file)


    self.update_state(state='PROGRESS',
            meta={'text': 'Save to database', 'progress' : 99})    

    prisma = Prisma()
    prisma.connect()
    
    updatedProject = prisma.project.update(
        where = {
            'id' :  projectId
        },
        data = {
            'isozones_running': False,
            'catchment_geojson': json.dumps(data),
            'branches_geojson': json.dumps(branches),
            'channel_length': dist_max.item(),
            'catchment_area': catchmentkm2.item(),
            'cummulative_channel_length': L_cum,
            'delta_h': delta_H,

        },
        )

    prisma.disconnect(5)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Finish', 'progress' : 100})
    return


def cumulative_length(geojson_featurecollection):
    total_length = 0.0
    for feature in geojson_featurecollection['features']:
        geom = shape(feature['geometry'])
        # For LineString or MultiLineString
        total_length += geom.length
    return total_length