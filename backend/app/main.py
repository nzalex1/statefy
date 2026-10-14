
from fastapi import FastAPI
from pydantic import BaseModel
import os
from app.api import health, resources

API_VERSION = "v1"
IS_PROD = os.getenv("ENV") == "production"

app = FastAPI(
    title="StateOps",
    description="Track state for everything",
    version="0.1.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json"
)

app.include_router(health.router)
app.include_router(
    resources.router,
    prefix=f"/api/{API_VERSION}"
)
