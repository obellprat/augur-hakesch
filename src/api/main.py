from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware
from dotenv import load_dotenv

from routers import catchment, file, task, isozones

from version import __version__

load_dotenv() # will search for .env file in local folder and load variables 

app = FastAPI(
    version=__version__,
)

# Set up Keycloak
keycloak_config = KeycloakConfiguration(
    url=os.getenv('PUBLIC_KEYCLOAK_URL'),
    realm="augur",
    client_id=os.getenv('AUTH_KEYCLOAK_ID'),
    client_secret=os.getenv('AUTH_KEYCLOAK_SECRET'),
    swagger_client_id="swagger-client",
    swagger_auth_pkce=True
)
excluded_routes = [
    "/docs",
    "/openapi.json",
]
# Add middleware with basic config
setup_keycloak_middleware(
    app,
    keycloak_configuration=keycloak_config,
    add_swagger_auth=True,
    exclude_patterns=excluded_routes,
)

app.mount("/data", StaticFiles(directory="data"), name="data")

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
app.include_router(isozones.router)
