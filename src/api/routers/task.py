from fastapi import APIRouter
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
import json
from celery.result import GroupResult

from calculations.calculations import app as celery_app
from helpers.celery_queue_wait import (
    resolve_queue_wait,
    resolve_queue_wait_for_pending_tasks,
)

router = APIRouter(prefix="/task",
    tags=["task"],)

_GROUP_TERMINAL_STATUSES = frozenset({"SUCCESS", "FAILURE", "REVOKED"})


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

def _attach_queue_wait(payload: dict, task_id: str) -> dict:
    qw = resolve_queue_wait(celery_app, task_id)
    if qw is not None:
        payload["queue_wait"] = qw
    return payload


def _group_payload_with_queue_wait(group_id: str, group_result: GroupResult) -> dict:
    result = _build_group_status_payload(group_id, group_result)
    if result["completed"] < result["total"] and result["status"] != "FAILURE":
        open_ids = [
            res.id for res in group_result.results
            if res.status not in _GROUP_TERMINAL_STATUSES
        ]
        qw = resolve_queue_wait_for_pending_tasks(celery_app, open_ids)
        if qw is not None:
            result["queue_wait"] = qw
    return result


@router.get("/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    try:
        result = {
            "task_id": task_id,
            "task_status": task_result.status,
            "task_result": json.dumps(task_result.result),
        }
    except Exception:
        result = {
            "task_id": task_id,
            "task_status": task_result.status,
            "task_result": str(task_result.result),
        }
    _attach_queue_wait(result, task_id)
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
                return JSONResponse(
                    _group_payload_with_queue_wait(resolved_group_id, resolved_group)
                )

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
        _attach_queue_wait(result, task_id)
        return JSONResponse(result)
    return JSONResponse(_group_payload_with_queue_wait(task_id, group_result))