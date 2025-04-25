from celery.result import AsyncResult
from fastapi import Body, FastAPI, Form, Request, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from typing import Annotated
import binascii

from worker import calculate_catchment
from worker import calculate_subcatchments


app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    f = open("index.html", "r")
    return f.read()

@app.get("/catchment/")
async def get_catchment(northing: float, easting: float, withRiverNetwork: bool = True):
    task = calculate_catchment.delay(northing, easting, withRiverNetwork)
    return JSONResponse({"task_id": task.id})

@app.post("/subcatchments/")
async def subcatchments(points_shapefile_zip: Annotated[bytes, File()]):
    task = calculate_subcatchments.delay(binascii.b2a_base64(points_shapefile_zip).decode('utf8'))
    return JSONResponse({"task_id": task.id})
    #task = calculate_subcatchments.delay(await points_shapefile_zip.file)
    #return JSONResponse({"task_id": task.id})

@app.get("/tasks/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)

@app.get("/file/{task_id}")
def get_file(task_id):
    task_result = AsyncResult(task_id)
    return Response(content=task_result.result, media_type="application/zip")


