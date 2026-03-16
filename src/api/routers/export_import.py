"""
API endpoints for project export and import.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from helpers.export_import import export_project, import_project
from helpers.user import get_user
from prisma.models import User

router = APIRouter(prefix="/project", tags=["project-export-import"])


@router.get("/export/{project_id}")
async def export_project_endpoint(
    project_id: str,
    user: User = Depends(get_user),
):
    """
    Export a project as a ZIP archive (DB data + TIF files).
    Returns application/zip with Content-Disposition for download.
    """
    try:
        zip_bytes = export_project(project_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    filename = f"project_{project_id}.augur.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/import")
async def import_project_endpoint(
    file: UploadFile = File(...),
    user: User = Depends(get_user),
):
    """
    Import a project from an AUGUR export ZIP file.
    Creates a new project with new IDs, linked to the importing user.
    Returns 201 with project_id and title.
    """
    if not file.filename or not (
        file.filename.endswith(".augur.zip")
        or file.filename.endswith(".augur")
        or file.filename.endswith(".zip")
    ):
        raise HTTPException(
            status_code=400,
            detail="File must be an AUGUR export (.augur.zip, .augur, or .zip)",
        )

    zip_bytes = await file.read()
    if len(zip_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = import_project(zip_bytes, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(content=result, status_code=201)
