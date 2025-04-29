import os
import time
from pysheds.grid import Grid
import fiona
from fiona.crs import CRS
import numpy as np
import json
import gc
import zipfile
import io
import binascii
import shutil
from celery.utils.log import get_task_logger

from celery import Celery


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
logger = get_task_logger(__name__)

@celery.task(name="calculate_catchment", bind=True)
def calculate_catchment(self, northing: float, easting: float, withRiverNetwork: bool):
    # Rertrieve and load DEM
    # ----------------------
    watershed = 'data/dir_3x3_3.tif'
    self.update_state(state='PROGRESS',
                meta={'text': 'Reading watershed'})
    grid = Grid.from_raster(watershed)
    #accugrid = Grid.from_raster(accumulation)

    # Compute flow directions
    # -------------------------------------
    #dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Compute flow directions'})
    dirmap = (1, 2, 3, 4, 5, 6, 7, 8)
    #fdir = grid.read_raster(watershed, window=(pointx - 50000, pointy - 50000, pointx + 50000, pointy + 50000), window_crs=grid.crs)
    fdir = grid.read_raster(watershed, window=(northing - 10000, easting - 10000, northing + 10000, easting + 10000), window_crs=grid.crs, dtype=np.uint8)
    
    grid.clip_to(fdir)
    small_view = grid.view(fdir)
    raster = grid.to_raster(fdir, 'data/temp/smallfdir.tif', target_view=small_view)

    del grid
    gc.collect()
    grid2 = Grid.from_raster('data/temp/smallfdir.tif')

    self.update_state(state='PROGRESS',
                meta={'text': 'Calculation accumulation'})
    acc = grid2.accumulation(fdir, dirmap=dirmap)
    print('Hier noch')
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

    # Create view
    catch_view = grid2.view(catch, dtype=np.uint8)

    self.update_state(state='PROGRESS',
                meta={'text': 'Polygonize catchment'})
    # Create a vector representation of the catchment mask
    shapes = grid2.polygonize(catch_view)

    # Specify schema
    schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'float:16'}
    }

    # Write shapefile
    
    self.update_state(state='PROGRESS',
                meta={'text': 'Creating geometry'})
    with fiona.open(f"data/temp/{self.request.id}.geojson", 'w',
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

    with open(f"data/temp/{self.request.id}.geojson", 'r') as file:
        data = json.load(file)
    os.remove(f"data/temp/{self.request.id}.geojson")

    rivernetwork = ''

    if withRiverNetwork:
        self.update_state(state='PROGRESS', meta={'text': 'Calculate river network'})
        # Extract river network
        rivernetwork = grid2.extract_river_network(fdir, acc > 10000, dirmap=dirmap)
    
    # Calculate distance to outlet from each cell
    #   -------------------------------------------
    self.update_state(state='PROGRESS', meta={'text': 'Calculate distance to outlet'})
    dist = grid2.distance_to_outlet(x=x_snap, y=y_snap, fdir=fdir, dirmap=dirmap,
                               xytype='coordinate')
    
    
    dist_max = np.max(dist[np.isfinite(dist)].astype(int)) * 2

    self.update_state(state='PROGRESS',
                meta={'text': 'Done'})
    returnobject = { 'max_outlet_distance': str(dist_max), 'northing' : str(x_snap), 'easting': str(y_snap), 'geometry' : data, 'rivernetwork' : rivernetwork}
    return returnobject



def calculate_subcatchment(id: float, requestid,  northing: float, easting: float):
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
            'properties': {'LABEL': 'int:10'}
    }

    # Write shapefile
    
    with fiona.open(f"data/{requestid}/shapefiles/{id}.shp", 'w',
                    driver='Shapefile',
                    crs=grid.crs.srs,
                    schema=schema) as c:
        i = 0
        for shape, value in shapes:
            rec = {}
            rec['geometry'] = shape
            rec['properties'] = {'LABEL' : id}
            rec['id'] = str(i)
            c.write(rec)
            i += 1

    return "OK"

@celery.task(name="calculate_subcatchments", bind=True)
def calculate_subcatchments(self, points_shapefile_zip_path):
    mybytes = binascii.a2b_base64(points_shapefile_zip_path.encode('utf8'))

    # Specify schema
    schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'int:10'}
    }
    self.update_state(state='PROGRESS',
                meta={'text': 'Generate new Shapefile'})
    os.mkdir(f"data/{self.request.id.__str__()}")
    os.mkdir(f"data/{self.request.id.__str__()}/output")
    os.mkdir(f"data/{self.request.id.__str__()}/shapefiles")

    
    self.update_state(state='PROGRESS',
            meta={'text': 'Unziping file'})
    with zipfile.ZipFile(io.BytesIO(mybytes)) as zip_ref:
        zip_ref.extractall(f"data/{self.request.id.__str__()}/")
        i = 0
        shapefilename = ""
        for shapefile in os.listdir(f"data/{self.request.id.__str__()}/"):
            if shapefile.endswith('.shp'):
                shapefilename = shapefile

        for feat in fiona.open(f"data/{self.request.id.__str__()}/{shapefilename}"):
            
            self.update_state(state='PROGRESS',
                meta={'text': f"Calculating subcatchment for #{i} at {feat['geometry']['coordinates'][0]}{feat['geometry']['coordinates'][1]}"})
            
            calculate_subcatchment(i, self.request.id.__str__(), feat['geometry']['coordinates'][0], feat['geometry']['coordinates'][1])
            
            i=i+1
    
    
    
    # Set the directory where the shapefiles are located
    shapefile_dir = f"data/{self.request.id.__str__()}/shapefiles/"

    # Create an empty list to store the merged shapefile
    merged_shapes = []

    self.update_state(state='PROGRESS',
                meta={'text': "Mergin output shapes to output.shp"})

    # Iterate through the shapefiles in the directory
    for shapefile in os.listdir(shapefile_dir):
        if shapefile.endswith('.shp'):
            # Open the shapefile using Fiona
            with fiona.open(shapefile_dir + shapefile) as f:
                # Iterate through the features in the shapefile
                for feature in f:
                    # Add the feature to the list of merged shapes
                    merged_shapes.append(feature)

    # Create a new Shapefile using Fiona
    with fiona.open(f"data/{self.request.id.__str__()}/output/output.shp", 'w', driver='ESRI Shapefile', crs=CRS.from_epsg(2056), schema=schema) as f:
        # Iterate through the list of merged shapes
        for shape in merged_shapes:
            f.write(shape)
  
    self.update_state(state='PROGRESS',
                meta={'text': "Ziping output.shp"})
    
    # zip the output
    shutil.make_archive(f"data/{self.request.id.__str__()}/output", 'zip', f"data/{self.request.id.__str__()}/output")
    in_file = open(f"data/{self.request.id.__str__()}/output.zip", "rb") # opening for [r]eading as [b]inary
    data = in_file.read()
    return data
