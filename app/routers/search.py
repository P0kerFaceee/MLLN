from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
from app.models.schemas import SearchResponse, SearchResult
from app.services.pipeline import search_pipeline

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_item(
    image: UploadFile = File(..., description="待检索图片"),
    top_k: int = Form(default=10, ge=1, le=50, description="返回TopK结果数量"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    result = search_pipeline(image=pil_image, top_k=top_k)

    search_results = [
        SearchResult(
            id=r["id"],
            category=r["category"],
            specification=r["specification"],
            description=r["description"],
            similarity=r["similarity"],
            image_url=r["image_url"],
        )
        for r in result["results"]
    ]

    return SearchResponse(
        results=search_results,
        query_category=result.get("query_category"),
        degraded=result.get("degraded", False),
        message=result["message"],
    )