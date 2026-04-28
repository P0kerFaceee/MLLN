from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image
import io
from app.models.schemas import LearnResponse
from app.services.pipeline import learn_pipeline
from app.config import UPLOAD_DIR

router = APIRouter()


@router.post("/upload", response_model=LearnResponse)
async def upload_item(
    image: UploadFile = File(..., description="零件图片"),
    category: str = Form(..., description="零件类别"),
    specification: str = Form(..., description="零件规格"),
    description: str = Form(None, description="零件描述"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    image_path = str(UPLOAD_DIR / image.filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    result = learn_pipeline(
        image=pil_image,
        category=category,
        specification=specification,
        description=description,
        image_path=image_path,
    )
    return LearnResponse(
        id=result.get("id", 0),
        category=category,
        specification=specification,
        description=description,
        status=result["status"],
        message=result["message"],
    )