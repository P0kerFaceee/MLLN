from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_placeholder():
    return {"status": "ok"}