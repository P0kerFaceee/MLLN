from typing import Optional, List, Dict, Set, Tuple
import logging
import numpy as np
import faiss
from app.config import DINOV2_FEATURE_DIM, FAISS_NLIST, FAISS_NPROBE, FAISS_INDEX_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS向量库管理：索引构建、动态添加、类别预过滤检索。"""

    def __init__(self, dim: int = DINOV2_FEATURE_DIM, nlist: int = FAISS_NLIST, nprobe: int = FAISS_NPROBE):
        self.dim = dim
        self.nlist = nlist
        self.nprobe = nprobe
        self._vectors: Dict[int, np.ndarray] = {}
        self._category_map: Dict[str, Set[int]] = {}
        self._index = None

    def _ensure_index(self):
        """确保索引已创建。数据量不足nlist时使用Flat索引，数据量>=nlist时切换到IVF。"""
        if self._index is None:
            total = len(self._vectors)
            if total < self.nlist:
                flat = faiss.IndexFlatL2(self.dim)
                self._index = faiss.IndexIDMap(flat)
                if total > 0:
                    all_vecs = np.stack(list(self._vectors.values())).astype(np.float32)
                    all_ids = np.array(list(self._vectors.keys()), dtype=np.int64)
                    self._index.add_with_ids(all_vecs, all_ids)
                logger.info(f"使用Flat+IDMap索引（数据量{total}）")
            else:
                quantizer = faiss.IndexFlatL2(self.dim)
                ivf = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist)
                self._index = faiss.IndexIDMap(ivf)
                all_vecs = np.stack(list(self._vectors.values())).astype(np.float32)
                ivf.train(all_vecs)
                ivf.nprobe = self.nprobe
                all_ids = np.array(list(self._vectors.keys()), dtype=np.int64)
                self._index.add_with_ids(all_vecs, all_ids)
                logger.info(f"使用IVF+IDMap索引，训练完成（数据量{total}）")

    def add(self, vector: np.ndarray, id: int, category: str):
        """动态添加向量到索引。part_id用于category_map关联。"""
        vector = vector.astype(np.float32).reshape(1, -1)
        self._vectors[id] = vector.squeeze()
        if category not in self._category_map:
            self._category_map[category] = set()
        self._category_map[category].add(id)

        self._ensure_index()
        self._index.add_with_ids(vector, np.array([id], dtype=np.int64))
        self.save()
        logger.info(f"向量添加成功: id={id}, category={category}")

    def search(self, query: np.ndarray, category: Optional[str] = None, top_k: int = 10) -> Tuple[List[int], List[float]]:
        """检索相似向量。category不为None时按类别预过滤，为None时全库检索（降级模式）。"""
        if self._index is None or self._index.ntotal == 0:
            return [], []

        query = query.astype(np.float32).reshape(1, -1)
        search_k = top_k * 5 if category else top_k
        distances, ids = self._index.search(query, search_k)

        logger.info(f"FAISS raw search: search_k={search_k}, top5 IDs={ids[0][:5].tolist()}, D={distances[0][:5].tolist()}")

        result_ids = []
        result_sims = []
        for dist, id_ in zip(distances[0], ids[0]):
            if id_ == -1:
                continue
            if category is not None:
                if id_ not in self._category_map.get(category, set()):
                    continue
            result_ids.append(int(id_))
            result_sims.append(float(dist))
            if len(result_ids) >= top_k:
                break

        return result_ids, result_sims

    def remove_ids(self, ids: List[int]):
        """从索引中移除指定ID的向量（重建不含这些ID的索引）。"""
        if self._index is None or self._index.ntotal == 0:
            return
        remaining_ids = []
        remaining_vecs = []
        id_map = self._index.id_map
        for i in range(self._index.ntotal):
            stored_id = id_map.at(i)
            if stored_id not in ids:
                remaining_ids.append(stored_id)
                remaining_vecs.append(self._vectors.get(stored_id, self._index.reconstruct(int(stored_id))))
        if len(remaining_vecs) > 0:
            all_vecs = np.stack(remaining_vecs).astype(np.float32)
            all_ids_np = np.array(remaining_ids, dtype=np.int64)
            flat = faiss.IndexFlatL2(self.dim)
            self._index = faiss.IndexIDMap(flat)
            self._index.add_with_ids(all_vecs, all_ids_np)
        else:
            self._index = None
        for id_ in ids:
            self._vectors.pop(id_, None)
        self.save()
        logger.info(f"已从索引移除 {len(ids)} 个向量，剩余 {len(self._vectors)} 个")

    def get_total_count(self) -> int:
        if self._index is not None:
            return self._index.ntotal
        return len(self._vectors)

    def get_categories(self) -> List[str]:
        return list(self._category_map.keys())

    def save(self):
        """保存FAISS索引到磁盘。"""
        if self._index is not None:
            faiss.write_index(self._index, str(FAISS_INDEX_PATH))
            logger.info(f"FAISS索引已保存: {FAISS_INDEX_PATH}")

    def load(self):
        """从磁盘加载FAISS索引。重建_vectors字典以支持remove_ids和distance_stats。"""
        if FAISS_INDEX_PATH.exists():
            self._index = faiss.read_index(str(FAISS_INDEX_PATH))
            # Populate _vectors from FAISS inner index
            id_map = self._index.id_map
            inner = self._index.index
            for i in range(self._index.ntotal):
                stored_id = id_map.at(i)
                vec = inner.reconstruct(i)
                self._vectors[stored_id] = vec.copy()
            logger.info(f"FAISS索引已加载: {FAISS_INDEX_PATH}, 向量数={self._index.ntotal}, _vectors={len(self._vectors)}")
        else:
            logger.info("FAISS索引文件不存在，将在首次添加时创建")

    def rebuild_category_map(self, part_records: List[Dict], photo_to_part: Dict[int, int]):
        """从parts表记录重建类别映射表。category_map[category] = set of photo_ids belonging to parts in that category."""
        self._category_map.clear()
        for part in part_records:
            cat = part["category"]
            if cat not in self._category_map:
                self._category_map[cat] = set()
            # Add all photo IDs that belong to this part
            for photo_id, part_id in photo_to_part.items():
                if part_id == part["id"]:
                    self._category_map[cat].add(photo_id)
        logger.info(f"类别映射已重建: {len(self._category_map)} 个类别")