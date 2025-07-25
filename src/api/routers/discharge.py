from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from celery import group

from calculations.discharge import construct_idf_curve, modifizierte_fliesszeit, prepare_discharge_hydroparameters, koella

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

