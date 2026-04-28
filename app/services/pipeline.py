import logging
import time
from PIL import Image
import numpy as np
from app.services.enhance import enhance_image
from app.services.dinov2 import extract_features
from app.services.bailian import classify_category
from app.services.vector_store import VectorStore
from app.services.metadata_store import MetadataStore
from app.config import FAISS_DEFAULT_TOP_K

logger = logging.getLogger(__name__)

vector_store = VectorStore()
metadata_store = MetadataStore()


def learn_pipeline(image: Image.Image, category: str, specification: str, description: str | None, image_path: str) -> dict:
    """学习端管道：图像增强→DINOv2→FAISS+元数据写入（整图提取特征，不依赖YOLO裁剪）。"""
    enhanced = enhance_image(image)
    features = extract_features(enhanced)

    new_id = int(time.time() * 1000) % (10 ** 9)
    vector_store.add(vector=features, id=new_id, category=category)
    metadata_store.add(id=new_id, category=category, specification=specification, description=description, image_path=image_path)

    logger.info(f"学习端入库成功: id={new_id}, category={category}")
    return {"status": "success", "id": new_id, "category": category, "specification": specification, "description": description, "message": "入库成功"}


def search_pipeline(image: Image.Image, top_k: int = FAISS_DEFAULT_TOP_K) -> dict:
    """使用端管道：百炼API(类别参考)→DINOv2→FAISS全库检索→元数据取回（整图提取特征）。"""
    enhanced = enhance_image(image)

    category = classify_category(enhanced)

    features = extract_features(enhanced)

    # 全库向量检索（DINOv2特征本身具备相似度匹配能力，百炼类别仅作参考展示）
    ids, similarities = vector_store.search(query=features, category=None, top_k=top_k)

    if len(ids) == 0:
        return {"results": [], "query_category": category, "degraded": category is None, "message": "未找到匹配项"}

    records = metadata_store.get_batch(ids)
    results = []
    for record, sim in zip(records, similarities):
        results.append({
            "id": record["id"],
            "category": record["category"],
            "specification": record["specification"],
            "description": record["description"],
            "similarity": sim,
            "image_url": record["image_path"],
        })

    return {
        "results": results,
        "query_category": category,
        "degraded": category is None,
        "message": f"检索完成，返回{len(results)}条结果" + ("（百炼API降级）" if category is None else ""),
    }