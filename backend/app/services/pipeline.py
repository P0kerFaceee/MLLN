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
    """使用端管道：百炼API类别→FAISS检索→元数据取回。
    百炼类别精确匹配底库时按类别预过滤，否则降级为全库检索。"""
    enhanced = enhance_image(image)

    category = classify_category(enhanced)

    features = extract_features(enhanced)
    logger.info(f"搜索特征向量范数: {np.linalg.norm(features):.2f}")

# 百炼类别精确匹配底库时按类别预过滤
    if category is not None and category in vector_store.get_categories():
        ids, similarities = vector_store.search(query=features, category=category, top_k=top_k)
        degraded = False
    else:
        # 百炼类别未匹配或不可用，降级为全库检索
        ids, similarities = vector_store.search(query=features, category=None, top_k=top_k)
        degraded = True

    if len(ids) == 0:
        return {"results": [], "query_category": category, "degraded": degraded, "message": "未找到匹配项"}

    records = metadata_store.get_batch(ids)
    record_map = {r["id"]: r for r in records}
    results = []
    for id_, sim in zip(ids, similarities):
        record = record_map[id_]
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
        "degraded": degraded,
        "message": f"检索完成，返回{len(results)}条结果" + ("（百炼类别未匹配底库，全库检索）" if degraded and category else "（百炼API降级，全库检索）" if degraded else ""),
    }