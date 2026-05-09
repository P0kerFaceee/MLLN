from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import learn, search, health, warehouse
from app.services.pipeline import vector_store, metadata_store
from app.config import UPLOAD_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store.load()
    # 从metadata重建类别映射（FAISS load只恢复了索引，内存映射需要从DB重建）
    rows = metadata_store._conn.execute(
        "SELECT id, category FROM metadata WHERE status = 'active'"
    ).fetchall()
    vector_store.rebuild_category_map([{"id": r["id"], "category": r["category"]} for r in rows])
    yield
    vector_store.save()
    metadata_store.close()


app = FastAPI(title="工业仓库物流识别系统", version="1.0.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(learn.router, prefix="/api/learn", tags=["学习端"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["仓库浏览"])

# mount必须在include_router之后，否则会拦截API请求
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/web", StaticFiles(directory="web", html=True), name="web")