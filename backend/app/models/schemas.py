from pydantic import BaseModel


# --- Spec Keys ---
class SpecKeyItem(BaseModel):
    id: int
    key_name: str
    unit: str | None = None

class SpecKeyCreate(BaseModel):
    key_name: str
    unit: str | None = None


# --- Photos ---
class PhotoItem(BaseModel):
    id: int
    part_id: int
    image_path: str
    angle: str | None = None


# --- Parts ---
class PartItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    photos: list[PhotoItem] = []

class PartListItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    thumbnail_urls: list[str] = []
    photo_count: int = 0

class PartCreate(BaseModel):
    name: str
    category: str
    specs: dict = {}
    description: str | None = None

class PartUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    specs: dict | None = None
    description: str | None = None


# --- Warehouse ---
class WarehouseResponse(BaseModel):
    parts: list[PartListItem]
    total: int

class PartDetailResponse(BaseModel):
    part: PartItem


# --- Search ---
class SearchResult(BaseModel):
    part_id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    best_similarity_pct: float
    best_photo_url: str
    best_photo_angle: str | None = None
    thumbnail_urls: list[str] = []
    total_photos: int

class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_category: str | None = None
    degraded: bool = False
    message: str


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    parts_count: int
    photos_count: int
    faiss_count: int
    categories: list[str]