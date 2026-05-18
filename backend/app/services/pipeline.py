import logging
import time
import numpy as np
from PIL import Image
from app.services.enhance import enhance_image
from app.services.vector_store import VectorStore
from app.services.part_store import PartStore
from app.config import FAISS_DEFAULT_TOP_K

logger = logging.getLogger(__name__)

vector_store = VectorStore()
part_store = PartStore()


def extract_features(image: Image.Image) -> np.ndarray:
    """Lazy-load DINOv2 so API startup/tests do not import heavy ML packages."""
    from app.services.dinov2 import extract_features as _extract_features

    return _extract_features(image)


def add_part_pipeline(
    name: str, category: str, specs: dict | None, description: str | None,
    images: list[tuple[Image.Image, str | None, str]],
) -> dict:
    """新增零件管道：创建part → 逐张照片(增强→DINOv2→FAISS写入)。"""
    part_id = int(time.time() * 1000) % (10 ** 9)
    part = part_store.add_part(id=part_id, name=name, category=category, specs=specs, description=description)

    photo_results = []
    for img, angle, image_path in images:
        enhanced = enhance_image(img)
        features = extract_features(enhanced)
        features = features / np.linalg.norm(features)

        photo_id = int(time.time() * 1000) % (10 ** 9)
        while photo_id == part_id:
            photo_id = (photo_id + 1) % (10 ** 9)

        vector_store.add(vector=features, id=photo_id, category=category)
        photo = part_store.add_photo(id=photo_id, part_id=part_id, image_path=image_path, angle=angle)
        photo_results.append(photo)

        _update_distance_stats(features, photo_id)
        time.sleep(0.001)

    logger.info(f"零件入库成功: part_id={part_id}, name={name}, {len(photo_results)}张照片")
    return {"part": part, "photos": photo_results}


def add_photo_pipeline(part_id: int, image: Image.Image, angle: str | None, image_path: str) -> dict:
    """给已有零件添加照片。"""
    part = part_store.get_part(part_id)
    if not part:
        raise ValueError(f"零件不存在: part_id={part_id}")

    enhanced = enhance_image(image)
    features = extract_features(enhanced)
    features = features / np.linalg.norm(features)

    photo_id = int(time.time() * 1000) % (10 ** 9)
    vector_store.add(vector=features, id=photo_id, category=part["category"])
    photo = part_store.add_photo(id=photo_id, part_id=part_id, image_path=image_path, angle=angle)

    _update_distance_stats(features, photo_id)

    logger.info(f"照片添加成功: photo_id={photo_id}, part_id={part_id}")
    return {"photo": photo}


def search_pipeline(
    image: Image.Image,
    top_k: int = FAISS_DEFAULT_TOP_K,
    category: str | None = None,
    specs: dict | None = None,
) -> dict:
    """使用端管道：前端上传类别/规格→FAISS检索→零件级聚合→返回零件结果。"""
    total_start = time.perf_counter()
    stage_start = time.perf_counter()
    enhanced = enhance_image(image, save_comparison=False)
    logger.info(f"搜索阶段耗时: image_preprocess={time.perf_counter() - stage_start:.3f}s")

    query_category = category.strip() if category else None
    query_specs = {
        str(k).strip(): str(v).strip()
        for k, v in (specs or {}).items()
        if str(k).strip() and str(v).strip()
    }

    stage_start = time.perf_counter()
    features = extract_features(enhanced)
    features = features / np.linalg.norm(features)
    logger.info(f"搜索阶段耗时: dinov2_extract={time.perf_counter() - stage_start:.3f}s")
    logger.info(f"搜索特征向量范数: {np.linalg.norm(features):.2f}")

    stage_start = time.perf_counter()
    if query_category is not None and query_category in vector_store.get_categories():
        photo_ids, distances = vector_store.search(query=features, category=query_category, top_k=top_k * 5)
        degraded = False
    else:
        photo_ids, distances = vector_store.search(query=features, category=None, top_k=top_k * 5)
        degraded = True
    logger.info(f"搜索阶段耗时: faiss_search={time.perf_counter() - stage_start:.3f}s")

    if len(photo_ids) == 0:
        logger.info(f"搜索总耗时: total={time.perf_counter() - total_start:.3f}s")
        return {"results": [], "query_category": query_category, "degraded": degraded, "message": "未找到匹配项"}

    def l2_to_cosine_similarity(l2_dist: float) -> float:
        cos_sim = 1 - (l2_dist ** 2) / 2
        return max(0.0, min(100.0, cos_sim * 100))

    stage_start = time.perf_counter()
    # Part-level aggregation
    photo_to_part = part_store.get_photo_to_part_map(photo_ids)
    photo_records = part_store.get_batch_photos(photo_ids)
    photo_map = {r["id"]: r for r in photo_records}

    part_groups: dict[int, list[tuple[int, float]]] = {}
    for photo_id, l2_dist in zip(photo_ids, distances):
        part_id = photo_to_part.get(photo_id)
        if part_id is None:
            continue
        part_groups.setdefault(part_id, []).append((photo_id, l2_dist))

    logger.info(f"搜索结果：{part_groups}")
    part_scores: list[dict] = []
    for part_id, photo_matches in part_groups.items():
        photo_matches.sort(key=lambda x: x[1])
        best_photo_id, best_l2 = photo_matches[0]
        best_similarity = l2_to_cosine_similarity(best_l2)

        boost_pct = 0.0
        if len(photo_matches) > 1:
            second_l2 = photo_matches[1][1]
            if best_l2 > 0:
                gap = second_l2 - best_l2
                boost_pct = max(0.0, min(5.0, gap * 10))
        logger.info(f"照片匹配：part_id={part_id}, photo_id={best_photo_id}, best_l2={best_l2:.1f},best_similarity={best_similarity},boost_pct={boost_pct}")
        final_similarity = min(100.0, 0.9*best_similarity + 0.1*boost_pct)

        part = part_store.get_part(part_id)
        if not part:
            continue
        spec_match_pct = _spec_match_pct(query_specs, part.get("specs") or {})
        if spec_match_pct > 0:
            final_similarity = min(100.0, final_similarity + spec_match_pct * 0.05)
        photos = part_store.get_photos_for_part(part_id)
        best_photo = photo_map.get(best_photo_id, {})
        thumbnails = [p["image_path"] for p in photos[:3]]

        part_scores.append({
            "part_id": part_id,
            "name": part["name"],
            "category": part["category"],
            "specs": part["specs"],
            "description": part["description"],
            "best_similarity_pct": round(final_similarity, 1),
            "best_photo_url": best_photo.get("image_path", ""),
            "best_photo_angle": best_photo.get("angle"),
            "thumbnail_urls": thumbnails,
            "total_photos": len(photos),
            "is_high_priority": final_similarity > 70.0,
        })

    high_priority = [p for p in part_scores if p["is_high_priority"]]
    normal = [p for p in part_scores if not p["is_high_priority"]]
    high_priority.sort(key=lambda x: x["best_similarity_pct"], reverse=True)
    normal.sort(key=lambda x: x["best_similarity_pct"], reverse=True)
    results = high_priority + normal
    results = results[:top_k]

    msg = f"检索完成，返回{len(results)}条零件结果"
    if degraded and query_category:
        msg += "（前端类别未匹配底库，全库检索）"
    elif degraded:
        msg += "（未选择类别，全库检索）"

    logger.info(f"搜索阶段耗时: part_aggregation={time.perf_counter() - stage_start:.3f}s")
    logger.info(f"搜索总耗时: total={time.perf_counter() - total_start:.3f}s")
    return {"results": results, "query_category": query_category, "degraded": degraded, "message": msg}


def _spec_match_pct(query_specs: dict, part_specs: dict) -> float:
    """Return a small exact/contains match score for user-provided spec hints."""
    if not query_specs or not part_specs:
        return 0.0

    matched = 0
    for key, query_value in query_specs.items():
        part_value = part_specs.get(key)
        if part_value is None:
            continue
        query_text = str(query_value).strip().lower()
        part_text = str(part_value).strip().lower()
        if query_text and (query_text == part_text or query_text in part_text or part_text in query_text):
            matched += 1

    return matched / len(query_specs) * 100.0


def _update_distance_stats(new_vector: np.ndarray, new_id: int):
    """增量更新L2距离统计量(dist_mean, dist_std)。"""
    existing_ids = list(vector_store._vectors.keys())
    if len(existing_ids) <= 1:
        part_store.update_stats("dist_mean", 0.0)
        part_store.update_stats("dist_std", 1.0)
        return

    new_vec = new_vector.astype(np.float32)
    distances = []
    for id_, vec in vector_store._vectors.items():
        if id_ == new_id:
            continue
        d = float(np.linalg.norm(new_vec - vec))
        distances.append(d)

    if not distances:
        return

    stats = part_store.get_stats()
    old_mean = stats.get("dist_mean", 0.0)
    old_std = stats.get("dist_std", 1.0)
    n_old = stats.get("dist_count", 0.0)

    new_dists = np.array(distances)
    n_new = len(new_dists)
    new_mean = float(new_dists.mean())
    new_std = float(new_dists.std()) if n_new > 1 else 0.0

    n_total = n_old + n_new
    if n_total > 0 and n_old > 0:
        combined_mean = (old_mean * n_old + new_mean * n_new) / n_total
        combined_var = (old_std ** 2 * n_old + new_std ** 2 * n_new) / n_total
        combined_std = float(np.sqrt(combined_var))
    else:
        combined_mean = new_mean
        combined_std = max(new_std, 1.0)

    part_store.update_stats("dist_mean", combined_mean)
    part_store.update_stats("dist_std", combined_std)
    part_store.update_stats("dist_count", n_total)
