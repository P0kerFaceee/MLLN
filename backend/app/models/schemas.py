from pydantic import BaseModel, Field
from typing import Optional


class LearnRequest(BaseModel):
    category: str = Field(..., description="零件类别")
    specification: str = Field(..., description="零件规格")
    description: Optional[str] = Field(None, description="零件描述信息")


class LearnResponse(BaseModel):
    id: int
    category: str
    specification: str
    description: Optional[str]
    status: str = Field(..., description="处理状态: success / pending_review / pending_complete")
    message: str


class SearchRequest(BaseModel):
    top_k: int = Field(default=10, description="返回TopK结果数量")


class SearchResult(BaseModel):
    id: int
    category: str
    specification: str
    description: Optional[str]
    similarity: float
    image_url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_category: Optional[str] = Field(None, description="百炼API判断的类别，降级时为None")
    degraded: bool = Field(default=False, description="是否为降级模式（百炼API不可用）")
    message: str


class WarehouseItem(BaseModel):
    id: int
    category: str
    specification: str
    description: Optional[str]
    image_url: str
    created_at: Optional[str]


class WarehouseResponse(BaseModel):
    items: list[WarehouseItem]
    total: int


class HealthResponse(BaseModel):
    status: str
    db_count: int
    faiss_count: int
    categories: list[str]