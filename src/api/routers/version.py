from fastapi import APIRouter, File
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse

from version import __version__

router = APIRouter(prefix="/version",
    tags=["version"],)

@router.get("/")
def get_version():
    return JSONResponse(content={"version": __version__})