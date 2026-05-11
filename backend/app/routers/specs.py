from fastapi import APIRouter, HTTPException
from app.models.schemas import SpecKeyItem, SpecKeyCreate
from app.services.pipeline import part_store

router = APIRouter()


@router.get("/keys", response_model=list[SpecKeyItem])
async def list_spec_keys():
    return part_store.list_spec_keys()


@router.post("/keys", response_model=SpecKeyItem)
async def create_spec_key(data: SpecKeyCreate):
    try:
        return part_store.add_spec_key(key_name=data.key_name, unit=data.unit)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/keys/{id}")
async def delete_spec_key(id: int):
    part_store.delete_spec_key(id)
    return {"status": "deleted"}