from fastapi import APIRouter
from app.models.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="statefy",
        version="0.1.0",
    )
