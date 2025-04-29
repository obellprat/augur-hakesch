from fastapi import APIRouter
from fastapi.responses import JSONResponse
from celery.result import AsyncResult

router = APIRouter(prefix="/task",
    tags=["task"],)

@router.get("/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)