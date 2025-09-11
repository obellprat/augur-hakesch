from fastapi import APIRouter, Depends, Response, HTTPException
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from pathlib import Path

router = APIRouter(prefix="/file",
    tags=["file"],)

@router.get("/{task_id}")
def get_file(task_id):
    task_result = AsyncResult(task_id)
    return Response(content=task_result.result, media_type="application/zip")


@router.get("/catchment/{project_id}")
async def download_catchment_geojson(project_id: str, user: User = Depends(get_user)):
    project = prisma.project.find_first(
        where={
            "id": project_id,
            "userId": user.id,
        }
    )

    if not project or not project.catchment_geojson:
        raise HTTPException(status_code=404, detail="Catchment GeoJSON not found")

    filename = f"catchment_{project_id}.geojson"
    return Response(
        content=project.catchment_geojson,
        media_type="application/geo+json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/branches/{project_id}")
async def download_branches_geojson(project_id: str, user: User = Depends(get_user)):
    project = prisma.project.find_first(
        where={
            "id": project_id,
            "userId": user.id,
        }
    )

    if not project or not project.branches_geojson:
        raise HTTPException(status_code=404, detail="Branches GeoJSON not found")

    filename = f"branches_{project_id}.geojson"
    return Response(
        content=project.branches_geojson,
        media_type="application/geo+json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/isozones/{project_id}")
async def download_isozones_tif(project_id: str, user: User = Depends(get_user)):
    project = prisma.project.find_first(
        where={
            "id": project_id,
            "userId": user.id,
        }
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tif_path = Path("data") / str(user.id) / project_id / "isozones_cog.tif"
    if not tif_path.exists():
        raise HTTPException(status_code=404, detail="isozones_cog.tif not found")

    return FileResponse(
        path=str(tif_path),
        media_type="image/tiff",
        filename=f"isozones_{project_id}.tif",
    )
