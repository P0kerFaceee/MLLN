from fastapi import FastAPI
from app.routers import learn, search, health

app = FastAPI(title="工业仓库物流识别系统", version="1.0.0")

app.include_router(health.router)
app.include_router(learn.router, prefix="/api/learn", tags=["学习端"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])