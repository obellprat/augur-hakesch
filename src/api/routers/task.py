from fastapi import APIRouter
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
import json
from celery.result import GroupResult

router = APIRouter(prefix="/task",
    tags=["task"],)

@router.get("/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    print(task_result.result)
    try:
        result = {
            "task_id": task_id,
                "task_status": task_result.status,
                "task_result": json.dumps(task_result.result)
            }
    except:
        result = {
            "task_id": task_id,
            "task_status": task_result.status,
            "task_result": str(task_result.result)
        }
    return JSONResponse(result)

@router.get("/group/{task_id}")
def get_group_status(task_id):
    group_result = GroupResult.restore(task_id)
    results = [
        {
            "task_id": res.id,
            "task_status": res.status,
            "task_result": json.dumps(res.result)
        }
        for res in group_result.results
    ]
    # Check for failure and get the first failure result if any
    failure = next((r for r in results if r["task_status"] == "FAILURE"), None)
    if failure:
        overall_status = "FAILURE"
        task_result = failure["task_result"]
    else:
        overall_status = "SUCCESS"
        task_result = None

    result = {
        "group_id": task_id,
        "tasks": results,
        "completed": group_result.completed_count(),
        "total": len(group_result.results),
        "status": overall_status,
        "task_result": task_result
    }
    return JSONResponse(result)