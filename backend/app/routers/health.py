from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.pipeline import part_store, vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        parts_count=part_store.count_parts(),
        photos_count=part_store.count_photos(),
        faiss_count=vector_store.get_total_count(),
        categories=part_store.get_categories(),
    )