
from fastapi import FastAPI
from pydantic import BaseModel
import os

IS_PROD = os.getenv("ENV") == "production"

app = FastAPI(
    title="StateOps",
    description="Track state for everything",
    version="0.1.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json"
)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="stateops",
        version="0.1.0",
    )


@app.get("/api/v1/resources")
async def list_resources():
    return {"resources": []}
