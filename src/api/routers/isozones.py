from fastapi import APIRouter, File
from fastapi.responses import JSONResponse
import binascii


from typing import Annotated

from calculations.isozones import calculate_isozones

router = APIRouter(prefix="/isozones",
    tags=["isozones"],)

@router.get("/")
async def get_catchment(northing: float, easting: float):
    task = calculate_isozones.delay(northing, easting)
    return JSONResponse({"task_id": task.id})