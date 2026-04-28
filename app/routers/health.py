from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.pipeline import vector_store, metadata_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        db_count=metadata_store.count(),
        faiss_count=vector_store.get_total_count(),
        categories=vector_store.get_categories(),
    )