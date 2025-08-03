from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from celery import group
import pandas as pd

from calculations.discharge import construct_idf_curve, modifizierte_fliesszeit, prepare_discharge_hydroparameters, koella, clark_wsl_modified
from calculations.nam import nam, get_curve_numbers, extract_dem

router = APIRouter(prefix="/discharge",
    tags=["discharge"],)

@router.get("/calculate_project")
def get_calculate_project(ProjectId:str, user: User = Depends(get_user)):
    try:
        project =  prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'IDF_Parameters' : True,
                'Point' : True,
                'Mod_Fliesszeit' : {
                    'include' :  {
                        'Annuality' : True
                    }
                },
                'Koella' : {
                    'include' :  {
                        'Annuality' : True
                    }       
                },
                'ClarkWSL' : {
                    'include' :  {
                        'Annuality' : True,
                        'Fractions' : True
                    }
                },
                'NAM' : {
                    'include' :  {
                        'Annuality' : True
                    }
                }
            }
        )

        doDoTasks = []

        for mod_fliesszeit in project.Mod_Fliesszeit:
            doDoTasks.append(modifizierte_fliesszeit.s(
                project.IDF_Parameters.P_low_1h, 
                project.IDF_Parameters.P_high_1h, 
                project.IDF_Parameters.P_low_24h, 
                project.IDF_Parameters.P_high_24h, 
                project.IDF_Parameters.rp_low, 
                project.IDF_Parameters.rp_high, 
                mod_fliesszeit.Annuality.number, 
                mod_fliesszeit.Vo20, 
                project.channel_length, 
                project.delta_h, 
                mod_fliesszeit.psi, 
                project.catchment_area, 
                mod_fliesszeit.id
            ))

        for koella_obj in project.Koella:
            doDoTasks.append(koella.s(
                project.IDF_Parameters.P_low_1h, 
                project.IDF_Parameters.P_high_1h, 
                project.IDF_Parameters.P_low_24h, 
                project.IDF_Parameters.P_high_24h, 
                project.IDF_Parameters.rp_low, 
                project.IDF_Parameters.rp_high, 
                koella_obj.Annuality.number, 
                koella_obj.Vo20, 
                project.channel_length, 
                project.catchment_area, 
                koella_obj.glacier_area, 
                koella_obj.id
            ))

                # TODO: get zone parameters from DB
        zone_parameters = {
                "Atyp 1": {'V0_20': 22.5, 'WSV': 12.5, 'psi': 0.475, 'alpha': 82},
                "Atyp 2": {'V0_20': 27.5, 'WSV': 22.5, 'psi': 0.375, 'alpha': 76},
                "Atyp 3": {'V0_20': 37.5, 'WSV': 37.5, 'psi': 0.15,  'alpha': 63.5},
                "Atyp 4": {'V0_20': 40,   'WSV': 42.5, 'psi': 0.1,   'alpha': 54},
                "Atyp 5": {'V0_20': 42.5, 'WSV': 52.5, 'psi': 0.075, 'alpha': 42},
                "Siedl.typ 1": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
                "Siedl.typ 2": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
                "Siedl.typ 3": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
            }

        for clark_wsl_obj in project.ClarkWSL:
            fractions_dict = [
                {"typ": f.ZoneParameterTyp, "pct": f.pct}
                for f in clark_wsl_obj.Fractions
            ]
            doDoTasks.append(clark_wsl_modified.s(
                P_low_1h=project.IDF_Parameters.P_low_1h,
                P_high_1h=project.IDF_Parameters.P_high_1h,
                P_low_24h=project.IDF_Parameters.P_low_24h,
                P_high_24h=project.IDF_Parameters.P_high_24h,
                rp_low=project.IDF_Parameters.rp_low,
                rp_high=project.IDF_Parameters.rp_high,
                discharge_types_parameters=zone_parameters,
                x=clark_wsl_obj.Annuality.number,
                fractions_dict=fractions_dict,
                clark_wsl=clark_wsl_obj.id,
                project_id=project.id,
                user_id=user.id,
                intensity_fn=None,
                dt=clark_wsl_obj.dt,
                pixel_area_m2=clark_wsl_obj.pixel_area_m2
            ))

        for nam_obj in project.NAM:
            doDoTasks.append(nam.s(
                P_low_1h=project.IDF_Parameters.P_low_1h,
                P_high_1h=project.IDF_Parameters.P_high_1h,
                P_low_24h=project.IDF_Parameters.P_low_24h,
                P_high_24h=project.IDF_Parameters.P_high_24h,
                rp_low=project.IDF_Parameters.rp_low,
                rp_high=project.IDF_Parameters.rp_high,
                x=nam_obj.Annuality.number,
                curve_number=nam_obj.curve_number,
                catchment_area=nam_obj.catchment_area,
                channel_length=nam_obj.channel_length,
                delta_h=nam_obj.delta_h,
                nam_id=nam_obj.id,
                project_id=project.id,
                user_id=user.id,
                TB_start=nam_obj.TB_start,
                istep=nam_obj.istep,
                tol=nam_obj.tol,
                max_iter=nam_obj.max_iter
            ))

        if len(doDoTasks) > 0:
            task = group(doDoTasks).apply_async()
            task.save()
            return JSONResponse({"task_id": task.id})

    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/modifizierte_fliesszeit")
def get_modifizierte_fliesszeit(ProjectId:str, ModFliesszeitId: int, user: User = Depends(get_user)):
    try:
        project =  prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'IDF_Parameters' : True,
                'Mod_Fliesszeit' : {
                    'include' :  {
                        'Annuality' : True
                    }
                }
            }
        )

        modFliesszeit = next((x for x in project.Mod_Fliesszeit if x.id == ModFliesszeitId), None)
        task = modifizierte_fliesszeit.delay(project.IDF_Parameters.P_low_1h, project.IDF_Parameters.P_high_1h, project.IDF_Parameters.P_low_24h, project.IDF_Parameters.P_high_24h, project.IDF_Parameters.rp_low, project.IDF_Parameters.rp_high, modFliesszeit.Annuality.number, modFliesszeit.Vo20, project.channel_length, project.delta_h, modFliesszeit.psi, project.catchment_area, modFliesszeit.id)
        return JSONResponse({"task_id": task.id}) 
    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/koella")
def get_koella(ProjectId:str, KoellaId: int, user: User = Depends(get_user)):
    try:
        project =  prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'IDF_Parameters' : True,
                'Koella' : {
                    'include' :  {
                        'Annuality' : True
                    }
                }
            }
        )

        koella_obj = next((x for x in project.Koella if x.id == KoellaId), None)
        task = koella.delay(project.IDF_Parameters.P_low_1h, project.IDF_Parameters.P_high_1h, project.IDF_Parameters.P_low_24h, project.IDF_Parameters.P_high_24h, project.IDF_Parameters.rp_low, project.IDF_Parameters.rp_high, koella_obj.Annuality.number, koella_obj.Vo20, project.channel_length, project.catchment_area, koella_obj.glacier_area, koella_obj.id)
        return JSONResponse({"task_id": task.id}) 
    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

"""
def clark_wsl_modified(self,
    discharge_types_parameters,# dict: ID -> {"WSV", "psi"}
    x,                         # Return period [y]
    fractions,                 # DataFrame with fractions by zone
    clark_wsl,                 # Clark WSL id
    project_id,                # Project ID for getting isozone raster
    user_id,                   # User ID for getting isozone raster
    intensity_fn=None,         # Precipitation intensity function: i(x, Tc) in mm/h
    dt=10,                     # Time step [min]
    pixel_area_m2=25           # Cell area [m²] (e.g. 5x5 m)
):
"""





@router.get("/clark-wsl")
def get_clark_wsl(ProjectId:str, ClarkWSLId: int, user: User = Depends(get_user)):
    try:
        project =  prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'IDF_Parameters' : True,
                'ClarkWSL' : {
                    'include' :  {
                        'Annuality' : True,
                        'Fractions' : True
                    }
                }
            }
        )

        # TODO: get zone parameters from DB
        zone_parameters = {
                "Atyp 1": {'V0_20': 22.5, 'WSV': 12.5, 'psi': 0.475, 'alpha': 82},
                "Atyp 2": {'V0_20': 27.5, 'WSV': 22.5, 'psi': 0.375, 'alpha': 76},
                "Atyp 3": {'V0_20': 37.5, 'WSV': 37.5, 'psi': 0.15,  'alpha': 63.5},
                "Atyp 4": {'V0_20': 40,   'WSV': 42.5, 'psi': 0.1,   'alpha': 54},
                "Atyp 5": {'V0_20': 42.5, 'WSV': 52.5, 'psi': 0.075, 'alpha': 42},
                "Siedl.typ 1": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
                "Siedl.typ 2": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
                "Siedl.typ 3": {'V0_20': 20, 'WSV': 20, 'psi': 0.4, 'alpha': 80},
            }

        clark_wsl_obj = next((x for x in project.ClarkWSL if x.id == ClarkWSLId), None)

        fractions_dict = [
            {"typ": f.ZoneParameterTyp, "pct": f.pct}
            for f in clark_wsl_obj.Fractions
        ]

        task = clark_wsl_modified.delay(
            P_low_1h=project.IDF_Parameters.P_low_1h,
            P_high_1h=project.IDF_Parameters.P_high_1h,
            P_low_24h=project.IDF_Parameters.P_low_24h,
            P_high_24h=project.IDF_Parameters.P_high_24h,
            rp_low=project.IDF_Parameters.rp_low,
            rp_high=project.IDF_Parameters.rp_high,
            discharge_types_parameters=zone_parameters,
            x=clark_wsl_obj.Annuality.number,
            fractions_dict=fractions_dict,
            clark_wsl=clark_wsl_obj.id,
            project_id=project.id,
            user_id=user.id,
            intensity_fn=None,
            dt=clark_wsl_obj.dt,
            pixel_area_m2=clark_wsl_obj.pixel_area_m2
        )
        return JSONResponse({"task_id": task.id})
    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/nam")
def get_nam(ProjectId:str, NAMId: int, 
            water_balance_mode: str = "simple",  # Options: "simple", "cumulative", "hybrid", "uniform", "conservative"
            storm_center_mode: str = "centroid",  # Options: "centroid", "discharge_point", "user_point"
            routing_method: str = "travel_time",  # Options: "travel_time", "isozone"
            user: User = Depends(get_user)):
    
    print(f"NAM request - ProjectId: {ProjectId}, NAMId: {NAMId}")
    print(f"Parameters - water_balance_mode: {water_balance_mode}, storm_center_mode: {storm_center_mode}, routing_method: {routing_method}")
    
    # Validate water_balance_mode
    valid_water_balance_modes = ["simple", "cumulative", "hybrid", "uniform", "conservative"]
    if water_balance_mode not in valid_water_balance_modes:
        print(f"Invalid water_balance_mode: {water_balance_mode}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid water_balance_mode: {water_balance_mode}. Valid options: {valid_water_balance_modes}"
        )
    
    # Validate storm_center_mode
    valid_storm_center_modes = ["centroid", "discharge_point", "user_point"]
    if storm_center_mode not in valid_storm_center_modes:
        print(f"Invalid storm_center_mode: {storm_center_mode}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid storm_center_mode: {storm_center_mode}. Valid options: {valid_storm_center_modes}"
        )
    
    # Validate routing_method
    valid_routing_methods = ["travel_time", "isozone"]
    if routing_method not in valid_routing_methods:
        print(f"Invalid routing_method: {routing_method}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid routing_method: {routing_method}. Valid options: {valid_routing_methods}"
        )
    
    print("Parameter validation passed")
    
    try:
        project = prisma.project.find_unique_or_raise(
            where={
                'userId': user.id,
                'id': ProjectId
            },
            include={
                'NAM': {
                    'include': {
                        'Annuality': True
                    }
                },
                'IDF_Parameters': True,
                'Point': True
            }
        )
        
        nam_obj = next((x for x in project.NAM if x.id == NAMId), None)
        
        if nam_obj is None:
            raise HTTPException(
                status_code=404,
                detail=f"NAM with ID {NAMId} not found in project {ProjectId}"
            )

        # Get discharge point coordinates from project if available
        discharge_point_lon_lat = None
        discharge_point_epsg2056 = None
        if hasattr(project, 'Point') and project.Point:
            # Keep original EPSG:2056 coordinates for elevation calculations
            discharge_point_epsg2056 = (project.Point.easting, project.Point.northing)
            
            # Convert from EPSG:2056 (Swiss coordinates) to geographic coordinates for routing
            try:
                import pyproj
                transformer = pyproj.Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
                lon, lat = transformer.transform(project.Point.easting, project.Point.northing)
                discharge_point_lon_lat = (lon, lat)
                print(f"Discharge point coordinates:")
                print(f"  EPSG:2056: ({project.Point.easting:.2f}, {project.Point.northing:.2f})")
                print(f"  WGS84: ({lon:.6f}, {lat:.6f})")
            except Exception as e:
                print(f"Warning: Could not convert discharge point coordinates: {e}")
                discharge_point_lon_lat = None
        
        task = nam.delay(
            P_low_1h=project.IDF_Parameters.P_low_1h,
            P_high_1h=project.IDF_Parameters.P_high_1h,
            P_low_24h=project.IDF_Parameters.P_low_24h,
            P_high_24h=project.IDF_Parameters.P_high_24h,
            rp_low=project.IDF_Parameters.rp_low,
            rp_high=project.IDF_Parameters.rp_high,
            x=nam_obj.Annuality.number,
            curve_number=nam_obj.curve_number,
            catchment_area=nam_obj.catchment_area,
            channel_length=nam_obj.channel_length,
            delta_h=nam_obj.delta_h,
            nam_id=nam_obj.id,
            project_id=project.id,
            user_id=user.id,
            TB_start=nam_obj.TB_start,
            istep=nam_obj.istep,
            tol=nam_obj.tol,
            max_iter=nam_obj.max_iter,
            water_balance_mode=water_balance_mode,
            storm_center_mode=storm_center_mode,
            discharge_point_lon_lat=discharge_point_lon_lat,
            discharge_point_epsg2056=discharge_point_epsg2056,
            use_kirpich=True,  # Use Kirpich method for travel time calculation
            routing_method=routing_method
        )
        return JSONResponse({"task_id": task.id})
    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/get_curve_numbers")
def get_curve_numbers_endpoint(ProjectId:str, user: User = Depends(get_user)):
    try:
        project = prisma.project.find_unique_or_raise(
            where={
                'userId': user.id,
                'id': ProjectId
            }
        )
        
        task = get_curve_numbers.delay(project.id, user.id)
        return JSONResponse({"task_id": task.id})
    except:
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/prepare_discharge_hydroparameters")
async def get_prepare_discharge_hydroparametersisozones(ProjectId:str, user: User = Depends(get_user)):
    try:
        project =  prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'Point' : True
            }
        )
        print(project)
        task = prepare_discharge_hydroparameters.delay(project.id, user.id, project.Point.easting, project.Point.northing)
        prisma.project.update(
            where = {
                'id' :  ProjectId
            },
            data = {
                'isozones_running': True,
                'isozones_taskid': task.id,
            },
            )
        return JSONResponse({"task_id": task.id})
    except:
        # Handle missing user scenario
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

@router.get("/extract_dem")
def get_extract_dem(ProjectId:str, user: User = Depends(get_user)):
    try:
        project = prisma.project.find_unique_or_raise(
            where={
                'userId': user.id,
                'id': ProjectId
            }
        )
        
        task = extract_dem.delay(project.id, user.id)
        return JSONResponse({"task_id": task.id})
    except:
        raise HTTPException(
            status_code=404,
            detail="Unable to retrieve project",
        )

