from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
from app.models.schemas import SearchResponse, SearchResult
from app.services.pipeline import search_pipeline

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_item(
    image: UploadFile = File(..., description="待检索图片"),
    top_k: int = Form(default=10, ge=1, le=50, description="返回TopK零件数量"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    result = search_pipeline(image=pil_image, top_k=top_k)

    search_results = [
        SearchResult(
            part_id=r["part_id"],
            name=r["name"],
            category=r["category"],
            specs=r["specs"],
            description=r["description"],
            best_similarity_pct=r["best_similarity_pct"],
            best_photo_url=r["best_photo_url"],
            best_photo_angle=r["best_photo_angle"],
            thumbnail_urls=r["thumbnail_urls"],
            total_photos=r["total_photos"],
        )
        for r in result["results"]
    ]

    return SearchResponse(
        results=search_results,
        query_category=result.get("query_category"),
        degraded=result.get("degraded", False),
        message=result["message"],
    )