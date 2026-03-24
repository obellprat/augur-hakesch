from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from typing import TypeAlias

router = APIRouter(prefix="/project",
    tags=["project"],)


@router.get("/by-id/{project_id}")
async def get_project(project_id: str, user: User = Depends(get_user)):
    project = prisma.project.find_first(
        where={
            'id': project_id,
            'userId': user.id
        },
        include={'Point': True}
    )
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return JSONResponse(project.model_dump(mode='json'))


@router.get("/")
async def get_projects(user: User = Depends(get_user)):
    projects = prisma.project.find_many(
        where = {
			'userId' : user.id
		},
		include = {
			'Point' : True
		}
    )

    return JSONResponse(([project.model_dump(mode='json') for project in projects]))