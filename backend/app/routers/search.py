from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
import json
from app.models.schemas import SearchResponse, SearchResult
from app.services.pipeline import search_pipeline

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_item(
    image: UploadFile = File(..., description="待检索图片"),
    top_k: int = Form(default=10, ge=1, le=50, description="返回TopK零件数量"),
    category: str | None = Form(default=None, description="前端选择/输入的类别"),
    specs: str = Form(default="{}", description="前端上传的规格JSON"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    try:
        specs_dict = json.loads(specs) if specs else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "规格参数必须是合法JSON")

    result = search_pipeline(image=pil_image, top_k=top_k, category=category, specs=specs_dict)

    search_results = [
        SearchResult(
            part_id=r["part_id"],
            name=r["name"],
            category=r["category"],
            specs=r["specs"],
            description=r["description"],
            best_similarity=r["best_similarity_pct"],
            best_photo_url=r["best_photo_url"],
            best_photo_angle=r["best_photo_angle"],
            thumbnail_urls=r["thumbnail_urls"],
            total_photos=r["total_photos"],
            is_high_priority=r["is_high_priority"],
        )
        for r in result["results"]
    ]

    return SearchResponse(
        results=search_results,
        query_category=result.get("query_category"),
        degraded=result.get("degraded", False),
        message=result["message"],
    )
