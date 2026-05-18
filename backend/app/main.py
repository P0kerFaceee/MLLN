import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import search, health, warehouse, specs
from app.services.pipeline import vector_store
from app.services.part_store import PartStore
from app.services.migration import run_migration
from app.services.dinov2 import warmup_model
from app.config import UPLOAD_DIR


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
    ]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup_model()
    vector_store.load()
    run_migration()
    part_store = PartStore()
    parts = part_store.list_parts()
    all_photo_ids = []
    for part in parts:
        photos = part_store.get_photos_for_part(part["id"])
        all_photo_ids.extend([p["id"] for p in photos])
    photo_to_part = part_store.get_photo_to_part_map(all_photo_ids) if all_photo_ids else {}
    vector_store.rebuild_category_map(parts, photo_to_part)
    yield
    vector_store.save()
    part_store.close()


app = FastAPI(title="工业仓库物流识别系统", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["系统状态"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["仓库浏览"])
app.include_router(specs.router, prefix="/api/specs", tags=["规格字典"])

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
