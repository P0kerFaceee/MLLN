import logging
import time
from PIL import Image
import numpy as np
from app.services.enhance import enhance_image
from app.services.yolo import yolo_detect_and_crop
from app.services.dinov2 import extract_features
from app.services.bailian import classify_category
from app.services.vector_store import VectorStore
from app.services.metadata_store import MetadataStore
from app.config import FAISS_DEFAULT_TOP_K

logger = logging.getLogger(__name__)

vector_store = VectorStore()
metadata_store = MetadataStore()


def learn_pipeline(image: Image.Image, category: str, specification: str, description: str | None, image_path: str) -> dict:
    """学习端管道：图像增强→YOLO→DINOv2→FAISS+元数据写入。"""
    enhanced = enhance_image(image)

    crop_result = yolo_detect_and_crop(enhanced)
    if crop_result is None:
        logger.warning("YOLO未检测到目标，标记为待人工审核")
        return {"status": "pending_review", "message": "未检测到目标区域，需人工审核", "id": 0}

    cropped_image, boxes = crop_result
    features = extract_features(cropped_image)

    new_id = int(time.time() * 1000) % (10 ** 9)
    vector_store.add(vector=features, id=new_id, category=category)
    metadata_store.add(id=new_id, category=category, specification=specification, description=description, image_path=image_path)

    logger.info(f"学习端入库成功: id={new_id}, category={category}")
    return {"status": "success", "id": new_id, "category": category, "specification": specification, "description": description, "message": "入库成功"}


def search_pipeline(image: Image.Image, top_k: int = FAISS_DEFAULT_TOP_K) -> dict:
    """使用端管道：YOLO→百炼API(类别预过滤)→DINOv2→FAISS检索→元数据取回。"""
    crop_result = yolo_detect_and_crop(image)
    if crop_result is None:
        return {"results": [], "query_category": None, "degraded": False, "message": "未检测到目标区域"}

    cropped_image, boxes = crop_result

    category = classify_category(cropped_image)
    degraded = category is None

    features = extract_features(cropped_image)

    search_category = category if not degraded else None
    ids, similarities = vector_store.search(query=features, category=search_category, top_k=top_k)

    if len(ids) == 0:
        return {"results": [], "query_category": category, "degraded": degraded, "message": "未找到匹配项"}

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
        "degraded": degraded,
        "message": f"检索完成，返回{len(results)}条结果" + ("（降级模式：全库检索）" if degraded else ""),
    }