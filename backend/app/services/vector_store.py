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
        self._vectors: dict[int, np.ndarray] = {}
        self._category_map: dict[str, set[int]] = {}
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
        """动态添加向量到索引，同时更新类别映射表。"""
        vector = vector.astype(np.float32).reshape(1, -1)
        self._vectors[id] = vector.squeeze()
        if category not in self._category_map:
            self._category_map[category] = set()
        self._category_map[category].add(id)

        self._ensure_index()
        self._index.add_with_ids(vector, np.array([id], dtype=np.int64))
        self.save()
        logger.info(f"向量添加成功: id={id}, category={category}")

    def search(self, query: np.ndarray, category: str | None = None, top_k: int = 10) -> tuple[list[int], list[float]]:
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

    def get_total_count(self) -> int:
        if self._index is not None:
            return self._index.ntotal
        return len(self._vectors)

    def get_categories(self) -> list[str]:
        return list(self._category_map.keys())

    def save(self):
        """保存FAISS索引到磁盘。"""
        if self._index is not None:
            faiss.write_index(self._index, str(FAISS_INDEX_PATH))
            logger.info(f"FAISS索引已保存: {FAISS_INDEX_PATH}")

    def load(self):
        """从磁盘加载FAISS索引。不在_vectors中填充占位符，避免重建索引时使用零向量。"""
        if FAISS_INDEX_PATH.exists():
            self._index = faiss.read_index(str(FAISS_INDEX_PATH))
            logger.info(f"FAISS索引已加载: {FAISS_INDEX_PATH}, 向量数={self._index.ntotal}")
        else:
            logger.info("FAISS索引文件不存在，将在首次添加时创建")

    def rebuild_category_map(self, records: list[dict]):
        """从metadata数据库记录重建类别映射表（服务器重启后调用）。"""
        self._category_map.clear()
        for r in records:
            cat = r["category"]
            id_ = r["id"]
            if cat not in self._category_map:
                self._category_map[cat] = set()
            self._category_map[cat].add(id_)
        logger.info(f"类别映射已重建: {len(self._category_map)} 个类别, 共 {len(records)} 条记录")