from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import learn, search, health
from app.services.pipeline import vector_store, metadata_store
from app.config import UPLOAD_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store.load()
    yield
    vector_store.save()
    metadata_store.close()


app = FastAPI(title="工业仓库物流识别系统", version="1.0.0", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/web", StaticFiles(directory="web", html=True), name="web")

app.include_router(health.router)
app.include_router(learn.router, prefix="/api/learn", tags=["学习端"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])