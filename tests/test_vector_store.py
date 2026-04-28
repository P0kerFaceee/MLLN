import numpy as np
from app.services.vector_store import VectorStore
from app.config import DINOV2_FEATURE_DIM, FAISS_NLIST, FAISS_NPROBE


def test_add_and_search():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    for i in range(10):
        vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
        category = "cat_a" if i < 5 else "cat_b"
        store.add(vector=vec, id=i + 1, category=category)

    query = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    ids, sims = store.search(query, category="cat_a", top_k=3)
    assert len(ids) > 0
    assert all(id_ in store._category_map.get("cat_a", set()) for id_ in ids)


def test_search_without_category_filter():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    for i in range(10):
        vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
        store.add(vector=vec, id=i + 1, category="cat_a" if i < 5 else "cat_b")

    query = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    ids, sims = store.search(query, category=None, top_k=5)
    assert len(ids) > 0


def test_immediate_search_after_add():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    store.add(vector=vec, id=1, category="test_cat")
    ids, sims = store.search(vec, category="test_cat", top_k=1)
    assert 1 in ids


def test_category_map_unknown_category():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    query = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    ids, sims = store.search(query, category="unknown_cat", top_k=3)
    assert len(ids) == 0