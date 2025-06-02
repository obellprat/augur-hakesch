from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from typing import TypeAlias

router = APIRouter(prefix="/project",
    tags=["project"],)

@router.get("/")
async def get_projects(user: User = Depends(get_user)):
    projects =  await prisma.project.find_many(
        where = {
			'userId' : user.id
		},
		include = {
			'Point' : True
		}
    )

    return JSONResponse(([project.model_dump(mode='json') for project in projects]))