from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from fastapi_keycloak_middleware import (
    AuthorizationMethod,
    KeycloakConfiguration,
    setup_keycloak_middleware,
)
from dotenv import load_dotenv
from helpers.prisma import prisma
from helpers.user import map_user
import logging
import uvicorn

from routers import (
    file,
    task,
    project,
    export_import,
    discharge,
    version,
    netcdf,
    monitoring,
    news,
    support,
)

from version import __version__

load_dotenv() # will search for .env file in local folder and load variables 

LOG = logging.getLogger(__name__)
LOG.info("API is starting up")
LOG.info(uvicorn.Config.asgi_version)

app = FastAPI(
    title="AUGUR API",
    version=__version__,
)

@app.on_event("startup")
async def startup():
    prisma.connect()
@app.on_event("shutdown")
async def shutdown():
    prisma.disconnect()

# Set up Keycloak
async def _scope_mapper(claim_auth):
    """Extract roles from Keycloak realm_access or resource_access into a flat list."""
    roles = []
    if isinstance(claim_auth, dict):
        roles = claim_auth.get("roles", []) or []
    elif isinstance(claim_auth, list):
        roles = claim_auth
    return roles if isinstance(roles, list) else []


keycloak_config = KeycloakConfiguration(
    url=os.getenv('PUBLIC_KEYCLOAK_URL'),
    realm="augur",
    client_id=os.getenv('AUTH_KEYCLOAK_ID'),
    client_secret=os.getenv('AUTH_KEYCLOAK_SECRET'),
    swagger_client_id="swagger-client",
    swagger_auth_pkce=True,
    authorization_method=AuthorizationMethod.CLAIM,
    authorization_claim="realm_access",
)
excluded_routes = [
    "/docs",
    "/openapi.json",
    "/api/openapi.json",
    "/data",
    "/version",
    "/netcdf",
]
# Add middleware with basic config
setup_keycloak_middleware(
    app,
    keycloak_configuration=keycloak_config,
    add_swagger_auth=True,
    exclude_patterns=excluded_routes,
    user_mapper=map_user,
    scope_mapper=_scope_mapper,
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

app.include_router(file.router)
app.include_router(task.router)
app.include_router(version.router)
app.include_router(project.router)
app.include_router(export_import.router)
app.include_router(discharge.router)
app.include_router(netcdf.router)
app.include_router(monitoring.router)
app.include_router(news.router)
app.include_router(support.router)


