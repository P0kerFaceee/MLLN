from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image
import io
import time
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

    # 生成唯一文件名避免冲突
    ext = image.filename.rsplit(".", 1)[-1] if "." in image.filename else "jpg"
    unique_name = f"{int(time.time() * 1000)}_{image.filename}"
    image_path = str(UPLOAD_DIR / unique_name)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # 存储web可访问的URL路径而非本地文件路径
    image_url = f"/uploads/{unique_name}"

    result = learn_pipeline(
        image=pil_image,
        category=category,
        specification=specification,
        description=description,
        image_path=image_url,
    )
    return LearnResponse(
        id=result.get("id", 0),
        category=category,
        specification=specification,
        description=description,
        status=result["status"],
        message=result["message"],
    )