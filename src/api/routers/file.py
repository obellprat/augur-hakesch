from fastapi import APIRouter, File
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/file",
    tags=["file"],)

@router.get("/{task_id}")
def get_file(task_id):
    task_result = AsyncResult(task_id)
    return Response(content=task_result.result, media_type="application/zip")
