from fastapi import APIRouter, Depends, Response, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from celery.result import AsyncResult
from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User
from pathlib import Path
import zipfile
import os
import shutil

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


@router.post("/upload-zip/{project_id}")
async def upload_zip_file(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_user)
):
    """
    Upload and extract a zip file to the project's data directory.
    Files will be extracted to data/{userId}/{projectId}/
    """
    # Verify project exists and belongs to user
    project = prisma.project.find_first(
        where={
            "id": project_id,
            "userId": user.id,
        }
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip file")
    
    # Create project data directory
    project_data_dir = Path("data") / str(user.id) / project_id
    project_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file temporarily
    temp_zip_path = project_data_dir / f"temp_{file.filename}"
    
    try:
        # Save the uploaded file
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract zip file
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            # Get list of files in zip
            file_list = zip_ref.namelist()
            
            # Extract all files to project directory
            zip_ref.extractall(project_data_dir)
        
        # Remove temporary zip file
        temp_zip_path.unlink()
        
        return {
            "message": f"Successfully uploaded and extracted {len(file_list)} files",
            "extracted_files": file_list,
            "destination": str(project_data_dir)
        }
        
    except zipfile.BadZipFile:
        # Clean up temp file if it exists
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        # Clean up temp file if it exists
        if temp_zip_path.exists():
            temp_zip_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing zip file: {str(e)}")


@router.get("/check-soil-shp/{project_id}")
async def check_soil_shp_exists(
    project_id: str,
    user: User = Depends(get_user)
):
    """
    Check if soil.shp file exists in the project's data directory.
    Returns true if the file exists, false otherwise.
    """
    # Verify project exists and belongs to user
    project = prisma.project.find_first(
        where={
            "id": project_id,
            "userId": user.id,
        }
    )
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if soil.shp exists in project data directory
    project_data_dir = Path("data") / str(user.id) / project_id
    soil_shp_path = project_data_dir / "soil.shp"
    
    return {
        "exists": soil_shp_path.exists(),
        "path": str(soil_shp_path)
    }
