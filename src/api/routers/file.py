from fastapi import APIRouter, File
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse

router = APIRouter(prefix="/file",
    tags=["file"],)

@router.get("/{task_id}")
def get_file(task_id):
    task_result = AsyncResult(task_id)
    return Response(content=task_result.result, media_type="application/zip")

@router.get("/isozones/{task_id}")
def get_file(task_id):
    return FileResponse(f"./data/" + task_id + "/isozones.tif", media_type="image/tiff")
