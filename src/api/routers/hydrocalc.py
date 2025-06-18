from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User

from calculations.hydrocalc import construct_idf_curve, modifizierte_fliesszeit, prepare_hydrocalc_hydroparameters, koella

router = APIRouter(prefix="/hydrocalc",
    tags=["hydrocalc"],)

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


@router.get("/prepare_hydrocalc_hydroparameters")
async def get_prepare_hydrocalc_hydroparametersisozones(ProjectId:str, user: User = Depends(get_user)):
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
        task = prepare_hydrocalc_hydroparameters.delay(project.id, user.id, project.Point.easting, project.Point.northing)
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

