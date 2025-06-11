from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User

from calculations.hakesch import modifizierte_fliesszeit, prepare_hakesch_hydroparameters

router = APIRouter(prefix="/hakesch",
    tags=["hakesch"],)

@router.get("/modifizierte_fliesszeit")
def modifizierte_fliesszeit(
    x,              # Return period: "2.3", "20", "100"
    Vo20,           # Wetting volume for 20-year event [mm]
    L,              # Channel length up to the watershed ridge [m] 
    delta_H,        # Elevation difference along L [m]
    psi,            # Peak flow coefficient [-]
    E,              # Catchment area [km²]
    intensity_fn,   # Rainfall intensity function: i(x, Tc) in mm/h
    TB_start=30,    # Initial value for TB [min]
    istep=5,        # Step size for TB [min]
    tol=5,          # Convergence tolerance [mm]
    max_iter=1000    # Max. iterations
):
    task = modifizierte_fliesszeit.delay(x, Vo20, L, delta_H, psi, E, intensity_fn, TB_start, istep, tol, max_iter)
    return JSONResponse({"task_id": task.id})



@router.get("/prepare_hakesch_hydroparameters")
async def get_prepare_hakesch_hydroparametersisozones(ProjectId:str, user: User = Depends(get_user)):
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
        task = prepare_hakesch_hydroparameters.delay(project.id, user.id, project.Point.easting, project.Point.northing)
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

