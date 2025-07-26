from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from celery import group
import pandas as pd

from calculations.discharge import construct_idf_curve, modifizierte_fliesszeit, prepare_discharge_hydroparameters, koella, clark_wsl_modified

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

