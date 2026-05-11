import io
import os
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from PIL import Image
from app.models.schemas import (
    WarehouseResponse, PartListItem, PartDetailResponse, PartItem, PhotoItem,
    PartCreate, PartUpdate, SpecKeyItem, SpecKeyCreate
)
from app.services.pipeline import add_part_pipeline, add_photo_pipeline, part_store, vector_store
from app.config import UPLOAD_DIR

router = APIRouter()


@router.get("/parts", response_model=WarehouseResponse)
async def list_parts(category: str | None = Query(None), name: str | None = Query(None)):
    parts = part_store.list_parts(category=category, name=name)
    items = []
    for p in parts:
        photos = part_store.get_photos_for_part(p["id"])
        thumbnails = [ph["image_path"] for ph in photos[:3]]
        items.append(PartListItem(
            id=p["id"], name=p["name"], category=p["category"],
            specs=p["specs"], description=p["description"],
            thumbnail_urls=thumbnails, photo_count=len(photos)
        ))
    return WarehouseResponse(parts=items, total=len(items))


@router.get("/parts/{part_id}", response_model=PartDetailResponse)
async def get_part_detail(part_id: int):
    part = part_store.get_part(part_id)
    if not part:
        raise HTTPException(404, "零件不存在")
    photos = part_store.get_photos_for_part(part_id)
    photo_items = [PhotoItem(**p) for p in photos]
    return PartDetailResponse(part=PartItem(
        id=part["id"], name=part["name"], category=part["category"],
        specs=part["specs"], description=part["description"],
        photos=photo_items
    ))


@router.post("/parts")
async def create_part(
    name: str = Form(...),
    category: str = Form(...),
    specs: str = Form("{}"),
    description: str = Form(None),
    images: list[UploadFile] = File(..., description="零件照片(多张)"),
    angles: list[str] = Form(None, description="角度标签列表(可选)"),
):
    import json
    try:
        specs_dict = json.loads(specs)
    except json.JSONDecodeError:
        specs_dict = {}

    existing = part_store.list_parts(category=category, name=name)
    if existing:
        raise HTTPException(400, f"类别'{category}'下已存在零件'{name}'")

    image_tuples = []
    for i, img_file in enumerate(images):
        image_bytes = await img_file.read()
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        ts = int(time.time() * 1000)
        ext = os.path.splitext(img_file.filename)[1] or ".jpg"
        filename = f"{ts}_{name}-{i}{ext}"
        filepath = UPLOAD_DIR / filename
        pil_image.save(filepath)
        web_path = f"/uploads/{filename}"

        angle = angles[i] if angles and i < len(angles) else None
        image_tuples.append((pil_image, angle, web_path))
        time.sleep(0.001)

    result = add_part_pipeline(name=name, category=category, specs=specs_dict, description=description, images=image_tuples)
    return result


@router.put("/parts/{part_id}")
async def update_part(part_id: int, update: PartUpdate):
    updated = part_store.update_part(
        id=part_id,
        name=update.name,
        category=update.category,
        specs=update.specs,
        description=update.description
    )
    if not updated:
        raise HTTPException(404, "零件不存在")
    if update.category:
        parts = part_store.list_parts()
        all_photos = part_store.get_batch_photos(list(vector_store._vectors.keys()))
        photo_to_part = {p["id"]: p["part_id"] for p in all_photos}
        vector_store.rebuild_category_map(parts, photo_to_part)
    return updated


@router.delete("/parts/{part_id}")
async def delete_part(part_id: int):
    photo_ids = part_store.delete_part(part_id)
    if not photo_ids:
        raise HTTPException(404, "零件不存在")
    vector_store.remove_ids(photo_ids)
    return {"status": "deleted", "part_id": part_id, "removed_photos": len(photo_ids)}


@router.post("/parts/{part_id}/photos")
async def add_photo_to_part(
    part_id: int,
    image: UploadFile = File(...),
    angle: str = Form(None),
):
    part = part_store.get_part(part_id)
    if not part:
        raise HTTPException(404, "零件不存在")

    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    ts = int(time.time() * 1000)
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"{ts}_{part['name']}-add{ext}"
    filepath = UPLOAD_DIR / filename
    pil_image.save(filepath)
    web_path = f"/uploads/{filename}"

    result = add_photo_pipeline(part_id=part_id, image=pil_image, angle=angle, image_path=web_path)
    return result


@router.delete("/parts/{part_id}/photos/{photo_id}")
async def delete_photo(part_id: int, photo_id: int):
    photo = part_store.get_photo(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")
    part_store.delete_photo(photo_id)
    vector_store.remove_ids([photo_id])
    return {"status": "deleted", "photo_id": photo_id}