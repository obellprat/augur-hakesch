from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from routers import catchment, file, task

from version import __version__


app = FastAPI(
    version=__version__,
)
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

app.include_router(catchment.router)
app.include_router(file.router)
app.include_router(task.router)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    f = open("index.html", "r")
    return f.read()


