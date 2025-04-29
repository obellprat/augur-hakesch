from fastapi import APIRouter, File
from fastapi.responses import JSONResponse
import binascii


from typing import Annotated

from calculations.catchment import calculate_catchment
from calculations.catchment import calculate_subcatchments

router = APIRouter(prefix="/catchment",
    tags=["catchment"],)

@router.get("/")
async def get_catchment(northing: float, easting: float, withRiverNetwork: bool = True):
    task = calculate_catchment.delay(northing, easting, withRiverNetwork)
    return JSONResponse({"task_id": task.id})

@router.post("/subcatchments/")
async def subcatchments(points_shapefile_zip: Annotated[bytes, File()]):
    task = calculate_subcatchments.delay(binascii.b2a_base64(points_shapefile_zip).decode('utf8'))
    return JSONResponse({"task_id": task.id})
    #task = calculate_subcatchments.delay(await points_shapefile_zip.file)
    #return JSONResponse({"task_id": task.id})