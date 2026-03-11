from fastapi import APIRouter
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
import json
from celery.result import GroupResult

router = APIRouter(prefix="/task",
    tags=["task"],)


def _build_group_status_payload(group_id: str, group_result: GroupResult):
    try:
        results = [
            {
                "task_id": res.id,
                "task_status": res.status,
                "task_result": json.dumps(res.result)
            }
            for res in group_result.results
        ]
    except:
        results = [
            {
                "task_id": res.id,
                "task_status": res.status,
                "task_result": str(res.result)
            }
            for res in group_result.results
        ]

    # Check for failure and get the first failure result if any
    failure = next((r for r in results if r["task_status"] == "FAILURE"), None)
    if failure:
        overall_status = "FAILURE"
        task_result = json.dumps(failure["task_result"])
    else:
        overall_status = "SUCCESS"
        task_result = None

    return {
        "group_id": group_id,
        "tasks": results,
        "completed": group_result.completed_count(),
        "total": len(group_result.results),
        "status": overall_status,
        "task_result": task_result
    }

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
    #task_result.forget()
    return JSONResponse(result)

@router.get("/group/{task_id}")
def get_group_status(task_id):
    group_result = GroupResult.restore(task_id)
    if group_result is None:
        # Fallback for non-group orchestration ids (e.g. chain ids).
        # If an orchestration task already produced a group_id, switch to group progress.
        task_result = AsyncResult(task_id)
        status = task_result.status
        resolved_group_id = None
        raw_result = task_result.result
        if isinstance(raw_result, dict):
            resolved_group_id = raw_result.get("group_id")

        if resolved_group_id:
            resolved_group = GroupResult.restore(resolved_group_id)
            if resolved_group is not None:
                return JSONResponse(_build_group_status_payload(resolved_group_id, resolved_group))

        result = {
            "group_id": task_id,
            "tasks": [{
                "task_id": task_id,
                "task_status": status,
                "task_result": str(task_result.result)
            }],
            "completed": 1 if status in ("SUCCESS", "FAILURE", "REVOKED") else 0,
            "total": 1,
            "status": "FAILURE" if status == "FAILURE" else ("SUCCESS" if status == "SUCCESS" else status),
            "task_result": str(task_result.result) if status == "FAILURE" else None
        }
        return JSONResponse(result)
    result = _build_group_status_payload(task_id, group_result)
    return JSONResponse(result)