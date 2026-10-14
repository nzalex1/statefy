from fastapi import APIRouter

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("")
def list_resources():
    return []
