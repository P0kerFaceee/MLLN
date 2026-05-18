from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel


# --- Spec Keys ---
class SpecKeyItem(BaseModel):
    id: int
    key_name: str
    unit: Optional[str] = None

class SpecKeyCreate(BaseModel):
    key_name: str
    unit: Optional[str] = None


# --- Photos ---
class PhotoItem(BaseModel):
    id: int
    part_id: int
    image_path: str
    angle: Optional[str] = None


# --- Parts ---
class PartItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: Optional[str] = None
    photos: List[PhotoItem] = []

class PartListItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: Optional[str] = None
    thumbnail_urls: List[str] = []
    photo_count: int = 0

class PartCreate(BaseModel):
    name: str
    category: str
    specs: dict = {}
    description: Optional[str] = None

class PartUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    specs: Optional[dict] = None
    description: Optional[str] = None


# --- Warehouse ---
class WarehouseResponse(BaseModel):
    parts: List[PartListItem]
    total: int

class PartDetailResponse(BaseModel):
    part: PartItem


# --- Search ---
class SearchResult(BaseModel):
    part_id: int
    name: str
    category: str
    specs: dict
    description: Optional[str] = None
    best_similarity: float
    best_photo_url: str
    best_photo_angle: Optional[str] = None
    thumbnail_urls: List[str] = []
    total_photos: int
    is_high_priority: bool = False

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query_category: Optional[str] = None
    degraded: bool = False
    message: str


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    parts_count: int
    photos_count: int
    faiss_count: int
    categories: List[str]
