from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from typing import TypeAlias

from calculations.isozones import calculate_isozones

router = APIRouter(prefix="/isozones",
    tags=["isozones"],)

@router.get("/")
async def get_isozones(ProjectId:str, user: User = Depends(get_user)):
    try:
        project =  await prisma.project.find_unique_or_raise(
            where = {
                'userId' : user.id,
                'id' :  ProjectId
            },
            include = {
                'Point' : True
            }
        )
        
        task = calculate_isozones.delay(project.id, project.Point.northing, project.Point.easting)
        await prisma.project.update(
            where = {
                'id' :  ProjectId
            },
            data = {
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




    