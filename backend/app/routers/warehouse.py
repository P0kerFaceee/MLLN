from fastapi import APIRouter
from app.models.schemas import WarehouseResponse, WarehouseItem
from app.services.pipeline import metadata_store

router = APIRouter()


@router.get("/list", response_model=WarehouseResponse)
def list_items():
    rows = metadata_store._conn.execute(
        "SELECT id, category, specification, description, image_path, created_at FROM metadata WHERE status = 'active' ORDER BY id DESC"
    ).fetchall()
    items = [
        WarehouseItem(
            id=r["id"],
            category=r["category"],
            specification=r["specification"],
            description=r["description"],
            image_url=r["image_path"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return WarehouseResponse(items=items, total=len(items))