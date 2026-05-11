# noyolo2 Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor MLLN from photo-level to part-level architecture: three-table data model (parts+photos+spec_keys), warehouse CRUD, search returns parts with Best-of-Part+boost strategy, L2 statistical percentage mapping, hard rules.

**Architecture:** Replace single metadata table with parts/photos/spec_keys SQLite tables. FAISS vectors stay photo-level but search results aggregate to part-level via pipeline post-processing. Remove LearnView, merge add-part into WarehouseView. Two-page app: Search + Warehouse.

**Tech Stack:** FastAPI, SQLite, FAISS, DINOv2, Vue 3 + Vite + Pinia, Axios

---

## File Structure

### New files to create:
- `backend/app/services/part_store.py` — PartStore class managing parts, photos, spec_keys tables + stats_meta
- `backend/app/services/migration.py` — One-shot metadata→parts+photos migration
- `backend/app/routers/specs.py` — spec_keys CRUD router
- `frontend/src/stores/warehouse.js` — Pinia store for warehouse CRUD state

### Files to delete:
- `backend/app/routers/learn.py`
- `frontend/src/views/LearnView.vue`

### Files to rewrite:
- `backend/app/services/pipeline.py` — learn→add_part, search→part-level aggregation
- `backend/app/services/vector_store.py` — category_map from parts, remove_ids, stats update
- `backend/app/models/schemas.py` — all new Pydantic models
- `backend/app/routers/warehouse.py` — full CRUD API
- `backend/app/routers/search.py` — part-level response
- `frontend/src/views/WarehouseView.vue` — CRUD + add-part
- `frontend/src/views/SearchView.vue` — part-level results

### Files to modify:
- `backend/app/main.py` — remove learn router, add specs router, migration on startup
- `backend/app/config.py` — add migration flag constant
- `backend/app/routers/health.py` — counts from new tables
- `backend/app/services/bailian.py` — _get_categories from parts
- `frontend/src/App.vue` — remove learn nav link
- `frontend/src/router/index.js` — remove learn route
- `frontend/src/stores/system.js` — update health fields
- `frontend/src/assets/styles/main.css` — remove learn styles, add CRUD styles

---

### Task 1: Database schema — PartStore + spec_keys

**Files:**
- Create: `backend/app/services/part_store.py`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Create PartStore class with three tables**

Create `backend/app/services/part_store.py`:

```python
import logging
import sqlite3
import json
from pathlib import Path
from app.config import DB_PATH

logger = logging.getLogger(__name__)


class PartStore:
    """管理 parts、photos、spec_keys 三表 + stats_meta 统计量。"""

    def __init__(self):
        self._conn = sqlite3.connect(str(DB_PATH))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                specs TEXT DEFAULT '{}',
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, name)
            );
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY,
                part_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                angle TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            );
            CREATE TABLE IF NOT EXISTS spec_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL UNIQUE,
                unit TEXT
            );
            CREATE TABLE IF NOT EXISTS stats_meta (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            );
        """)
        self._conn.commit()
        logger.info("数据库表已创建/确认")

    def add_part(self, id: int, name: str, category: str, specs: dict | None = None, description: str | None = None) -> dict:
        specs_json = json.dumps(specs or {}, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO parts (id, name, category, specs, description) VALUES (?, ?, ?, ?, ?)",
            (id, name, category, specs_json, description)
        )
        self._conn.commit()
        return {"id": id, "name": name, "category": category, "specs": specs or {}, "description": description}

    def get_part(self, id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM parts WHERE id = ? AND status = 'active'", (id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["specs"] = json.loads(result["specs"])
        return result

    def list_parts(self, category: str | None = None, name: str | None = None) -> list[dict]:
        query = "SELECT * FROM parts WHERE status = 'active'"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")
        query += " ORDER BY id DESC"
        rows = self._conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            r = dict(row)
            r["specs"] = json.loads(r["specs"])
            results.append(r)
        return results

    def update_part(self, id: int, name: str | None = None, category: str | None = None, specs: dict | None = None, description: str | None = None):
        part = self.get_part(id)
        if not part:
            return None
        updates = {}
        if name is not None:
            updates["name"] = name
        if category is not None:
            updates["category"] = category
        if specs is not None:
            updates["specs"] = json.dumps(specs, ensure_ascii=False)
        if description is not None:
            updates["description"] = description
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            self._conn.execute(f"UPDATE parts SET {set_clause} WHERE id = ?", (*updates.values(), id))
            self._conn.commit()
        return self.get_part(id)

    def delete_part(self, id: int) -> list[int]:
        photo_ids = [r["id"] for r in self._conn.execute("SELECT id FROM photos WHERE part_id = ? AND status = 'active'", (id,)).fetchall()]
        self._conn.execute("UPDATE parts SET status = 'deleted' WHERE id = ?", (id,))
        self._conn.execute("UPDATE photos SET status = 'deleted' WHERE part_id = ?", (id,))
        self._conn.commit()
        return photo_ids

    def count_parts(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM parts WHERE status = 'active'").fetchone()
        return row["cnt"]

    def get_categories(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT category FROM parts WHERE status = 'active' ORDER BY category").fetchall()
        return [r["category"] for r in rows]

    def add_photo(self, id: int, part_id: int, image_path: str, angle: str | None = None) -> dict:
        self._conn.execute(
            "INSERT INTO photos (id, part_id, image_path, angle) VALUES (?, ?, ?, ?)",
            (id, part_id, image_path, angle)
        )
        self._conn.commit()
        return {"id": id, "part_id": part_id, "image_path": image_path, "angle": angle}

    def get_photos_for_part(self, part_id: int) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM photos WHERE part_id = ? AND status = 'active' ORDER BY id", (part_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_photo(self, id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM photos WHERE id = ? AND status = 'active'", (id,)).fetchone()
        return dict(row) if row else None

    def delete_photo(self, id: int):
        self._conn.execute("UPDATE photos SET status = 'deleted' WHERE id = ?", (id,))
        self._conn.commit()

    def count_photos(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM photos WHERE status = 'active'").fetchone()
        return row["cnt"]

    def add_spec_key(self, key_name: str, unit: str | None = None) -> dict:
        self._conn.execute("INSERT INTO spec_keys (key_name, unit) VALUES (?, ?)", (key_name, unit))
        self._conn.commit()
        return {"key_name": key_name, "unit": unit}

    def list_spec_keys(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM spec_keys ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def delete_spec_key(self, id: int):
        self._conn.execute("DELETE FROM spec_keys WHERE id = ?", (id,))
        self._conn.commit()

    def get_stats(self) -> dict:
        rows = self._conn.execute("SELECT key, value FROM stats_meta").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def update_stats(self, key: str, value: float):
        self._conn.execute("INSERT OR REPLACE INTO stats_meta (key, value) VALUES (?, ?)", (key, value))
        self._conn.commit()

    def get_batch_photos(self, ids: list[int]) -> list[dict]:
        rows = self._conn.execute(
            f"SELECT * FROM photos WHERE id IN ({','.join(map(str, ids))}) AND status = 'active'"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_photo_to_part_map(self, photo_ids: list[int]) -> dict[int, int]:
        """返回 photo_id → part_id 的映射。"""
        rows = self._conn.execute(
            f"SELECT id, part_id FROM photos WHERE id IN ({','.join(map(str, photo_ids))}) AND status = 'active'"
        ).fetchall()
        return {r["id"]: r["part_id"] for r in rows}

    def close(self):
        self._conn.close()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/part_store.py
git commit -m "feat: add PartStore with parts/photos/spec_keys/stats_meta tables"
```

---

### Task 2: Data migration from metadata to parts+photos

**Files:**
- Create: `backend/app/services/migration.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create migration script**

Create `backend/app/services/migration.py`:

```python
"""将旧 metadata 表数据迁移到 parts + photos 表。
同 category+specification 组合归为一个 part，name=specification，specs={}。
FAISS 索引 ID 不变（photo.id = 原 metadata.id）。"""
import logging
import sqlite3
import json
import time
from app.config import DB_PATH

logger = logging.getLogger(__name__)


def needs_migration() -> bool:
    """检查是否需要迁移：metadata 表存在且 parts 表为空。"""
    conn = sqlite3.connect(str(DB_PATH))
    # Check metadata table exists
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "metadata" not in tables:
        conn.close()
        return False
    # Check parts table is empty (or doesn't exist)
    try:
        count = conn.execute("SELECT COUNT(*) FROM parts WHERE status = 'active'").fetchone()[0]
        conn.close()
        return count == 0
    except sqlite3.OperationalError:
        conn.close()
        return True


def run_migration():
    """执行迁移：metadata → parts + photos。"""
    if not needs_migration():
        logger.info("无需迁移，跳过")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Ensure parts/photos/spec_keys/stats_meta tables exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            specs TEXT DEFAULT '{}',
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, name)
        );
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY,
            part_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            angle TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (part_id) REFERENCES parts(id)
        );
        CREATE TABLE IF NOT EXISTS spec_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_name TEXT NOT NULL UNIQUE,
            unit TEXT
        );
        CREATE TABLE IF NOT EXISTS stats_meta (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL
        );
    """)
    conn.commit()

    # Read all active metadata rows
    rows = conn.execute("SELECT * FROM metadata WHERE status = 'active'").fetchall()
    logger.info(f"迁移: {len(rows)} 条 metadata 记录")

    # Group by (category, specification) → one part per group
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row["category"], row["specification"])
        groups.setdefault(key, []).append(dict(row))

    # Create parts and photos
    for (category, specification), items in groups.items():
        # Use first item's id as part_id (smallest id in group for stability)
        part_id = min(item["id"] for item in items)
        # Avoid collision: if part_id == a photo id from another group, offset
        try:
            conn.execute(
                "INSERT INTO parts (id, name, category, specs, description) VALUES (?, ?, ?, ?, ?)",
                (part_id, specification, category, json.dumps({}, ensure_ascii=False), items[0]["description"])
            )
        except sqlite3.IntegrityError:
            # ID collision with a photo, use timestamp-based id instead
            part_id = int(time.time() * 1000) % (10 ** 9)
            conn.execute(
                "INSERT INTO parts (id, name, category, specs, description) VALUES (?, ?, ?, ?, ?)",
                (part_id, specification, category, json.dumps({}, ensure_ascii=False), items[0]["description"])
            )

        for item in items:
            conn.execute(
                "INSERT INTO photos (id, part_id, image_path, angle, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (item["id"], part_id, item["image_path"], None, item["status"], item["created_at"])
            )

    conn.commit()
    logger.info(f"迁移完成: {len(groups)} 个零件, {len(rows)} 张照片")

    # Don't drop metadata table yet — keep as backup
    conn.close()
```

- [ ] **Step 2: Add migration call to main.py lifespan**

Modify `backend/app/main.py` — in the `lifespan` function, after loading FAISS and before rebuilding category map, add migration:

```python
from app.services.migration import run_migration
# ... in lifespan function, after vector_store.load():
run_migration()
# Then rebuild category map from parts:
records = part_store.list_parts()
vector_store.rebuild_category_map(records)
```

Replace `metadata_store` import/usage with `part_store` throughout main.py. Remove `learn` router import and registration. Add `specs` router.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/migration.py backend/app/main.py
git commit -m "feat: add metadata→parts+photos migration, update main.py lifespan"
```

---

### Task 3: Pydantic schemas rewrite

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Rewrite schemas.py with new models**

Replace entire `backend/app/models/schemas.py`:

```python
from pydantic import BaseModel


# --- Spec Keys ---
class SpecKeyItem(BaseModel):
    id: int
    key_name: str
    unit: str | None = None

class SpecKeyCreate(BaseModel):
    key_name: str
    unit: str | None = None


# --- Photos ---
class PhotoItem(BaseModel):
    id: int
    part_id: int
    image_path: str
    angle: str | None = None


# --- Parts ---
class PartItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    photos: list[PhotoItem] = []

class PartListItem(BaseModel):
    id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    thumbnail_urls: list[str] = []
    photo_count: int = 0

class PartCreate(BaseModel):
    name: str
    category: str
    specs: dict = {}
    description: str | None = None

class PartUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    specs: dict | None = None
    description: str | None = None


# --- Warehouse ---
class WarehouseResponse(BaseModel):
    parts: list[PartListItem]
    total: int

class PartDetailResponse(BaseModel):
    part: PartItem


# --- Search ---
class SearchResult(BaseModel):
    part_id: int
    name: str
    category: str
    specs: dict
    description: str | None = None
    best_similarity_pct: float
    best_photo_url: str
    best_photo_angle: str | None = None
    thumbnail_urls: list[str] = []
    total_photos: int

class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_category: str | None = None
    degraded: bool = False
    message: str


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    parts_count: int
    photos_count: int
    faiss_count: int
    categories: list[str]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: rewrite Pydantic schemas for part-level architecture"
```

---

### Task 4: VectorStore adjustments — category_map from parts, remove_ids, stats

**Files:**
- Modify: `backend/app/services/vector_store.py`

- [ ] **Step 1: Add remove_ids and stats methods to VectorStore**

In `backend/app/services/vector_store.py`, add these methods to the `VectorStore` class:

```python
    def remove_ids(self, ids: list[int]):
        """从索引中移除指定ID的向量（重建不含这些ID的索引）。"""
        if self._index is None or self._index.ntotal == 0:
            return
        # Collect remaining vectors
        remaining_ids = []
        remaining_vecs = []
        id_map = self._index.id_map
        for i in range(self._index.ntotal):
            stored_id = id_map.at(i)
            if stored_id not in ids and stored_id in self._vectors:
                remaining_ids.append(stored_id)
                remaining_vecs.append(self._vectors[stored_id])
        # Rebuild index
        if len(remaining_vecs) > 0:
            all_vecs = np.stack(remaining_vecs).astype(np.float32)
            all_ids_np = np.array(remaining_ids, dtype=np.int64)
            flat = faiss.IndexFlatL2(self.dim)
            self._index = faiss.IndexIDMap(flat)
            self._index.add_with_ids(all_vecs, all_ids_np)
        else:
            self._index = None
        # Clean _vectors
        for id_ in ids:
            self._vectors.pop(id_, None)
        self.save()
        logger.info(f"已从索引移除 {len(ids)} 个向量，剩余 {len(self._vectors)} 个")
```

Also update `rebuild_category_map` to accept part-level records (with photos mapping):

```python
    def rebuild_category_map(self, part_records: list[dict], photo_to_part: dict[int, int]):
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/vector_store.py
git commit -m "feat: add remove_ids and part-level rebuild_category_map to VectorStore"
```

---

### Task 5: Pipeline rewrite — add_part_pipeline + part-level search_pipeline

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Modify: `backend/app/services/bailian.py`

- [ ] **Step 1: Rewrite pipeline.py**

Replace entire `backend/app/services/pipeline.py`:

```python
import logging
import time
import numpy as np
from PIL import Image
from app.services.enhance import enhance_image
from app.services.dinov2 import extract_features
from app.services.bailian import classify_category
from app.services.vector_store import VectorStore
from app.services.part_store import PartStore
from app.config import FAISS_DEFAULT_TOP_K

logger = logging.getLogger(__name__)

vector_store = VectorStore()
part_store = PartStore()


def add_part_pipeline(
    name: str, category: str, specs: dict | None, description: str | None,
    images: list[tuple[Image.Image, str | None, str]],  # (PIL image, angle, image_path)
) -> dict:
    """新增零件管道：创建part → 逐张照片(增强→DINOv2→FAISS写入)。"""
    part_id = int(time.time() * 1000) % (10 ** 9)
    part = part_store.add_part(id=part_id, name=name, category=category, specs=specs, description=description)

    photo_results = []
    for img, angle, image_path in images:
        enhanced = enhance_image(img)
        features = extract_features(enhanced)

        photo_id = int(time.time() * 1000) % (10 ** 9)
        # Ensure photo_id != part_id
        while photo_id == part_id:
            photo_id = (photo_id + 1) % (10 ** 9)

        vector_store.add(vector=features, id=photo_id, category=category, part_id=part_id)
        photo = part_store.add_photo(id=photo_id, part_id=part_id, image_path=image_path, angle=angle)
        photo_results.append(photo)

        # Incremental stats update
        _update_distance_stats(features, photo_id)
        time.sleep(0.001)  # Ensure unique timestamp for next id

    logger.info(f"零件入库成功: part_id={part_id}, name={name}, {len(photo_results)}张照片")
    return {"part": part, "photos": photo_results}


def add_photo_pipeline(part_id: int, image: Image.Image, angle: str | None, image_path: str) -> dict:
    """给已有零件添加照片。"""
    part = part_store.get_part(part_id)
    if not part:
        raise ValueError(f"零件不存在: part_id={part_id}")

    enhanced = enhance_image(image)
    features = extract_features(enhanced)

    photo_id = int(time.time() * 1000) % (10 ** 9)
    vector_store.add(vector=features, id=photo_id, category=part["category"], part_id=part_id)
    photo = part_store.add_photo(id=photo_id, part_id=part_id, image_path=image_path, angle=angle)

    _update_distance_stats(features, photo_id)

    logger.info(f"照片添加成功: photo_id={photo_id}, part_id={part_id}")
    return {"photo": photo}


def search_pipeline(image: Image.Image, top_k: int = FAISS_DEFAULT_TOP_K) -> dict:
    """使用端管道：百炼类别→FAISS检索→零件级聚合→兜底规则→返回零件结果。"""
    enhanced = enhance_image(image)

    category = classify_category(enhanced)

    features = extract_features(enhanced)
    logger.info(f"搜索特征向量范数: {np.linalg.norm(features):.2f}")

    # FAISS search (photo-level)
    if category is not None and category in vector_store.get_categories():
        photo_ids, distances = vector_store.search(query=features, category=category, top_k=top_k * 5)
        degraded = False
    else:
        photo_ids, distances = vector_store.search(query=features, category=None, top_k=top_k * 5)
        degraded = True

    if len(photo_ids) == 0:
        return {"results": [], "query_category": category, "degraded": degraded, "message": "未找到匹配项"}

    # L2 → percentage mapping
    stats = part_store.get_stats()
    dist_mean = stats.get("dist_mean", 1000.0)
    dist_std = stats.get("dist_std", 500.0)
    if dist_std == 0:
        dist_std = 1.0

    def l2_to_pct(l2_dist: float) -> float:
        return max(0.0, min(100.0, (1 - (l2_dist - dist_mean) / (3 * dist_std)) * 100))

    # Part-level aggregation
    photo_to_part = part_store.get_photo_to_part_map(photo_ids)
    photo_records = part_store.get_batch_photos(photo_ids)
    photo_map = {r["id"]: r for r in photo_records}

    # Group photos by part_id
    part_groups: dict[int, list[tuple[int, float]]] = {}  # part_id → [(photo_id, l2_distance)]
    for photo_id, l2_dist in zip(photo_ids, distances):
        part_id = photo_to_part.get(photo_id)
        if part_id is None:
            continue
        part_groups.setdefault(part_id, []).append((photo_id, l2_dist))

    # Compute per-part scores: Best-of-Part + boost
    part_scores: list[dict] = []
    for part_id, photo_matches in part_groups.items():
        # Sort by L2 distance (ascending = more similar first)
        photo_matches.sort(key=lambda x: x[1])
        best_photo_id, best_l2 = photo_matches[0]
        best_pct = l2_to_pct(best_l2)

        # Boost: if second photo is also close
        boost_pct = 0.0
        if len(photo_matches) > 1:
            second_l2 = photo_matches[1][1]
            # Closer second photo → more boost, capped at 5%
            ratio = (second_l2 - best_l2) / best_l2 if best_l2 > 0 else 999
            boost_pct = max(0.0, min(5.0, (1 - ratio) * 3))

        final_pct = min(100.0, best_pct + boost_pct)

        part = part_store.get_part(part_id)
        if not part:
            continue
        photos = part_store.get_photos_for_part(part_id)
        best_photo = photo_map.get(best_photo_id, {})
        thumbnails = [p["image_path"] for p in photos[:3]]

        part_scores.append({
            "part_id": part_id,
            "name": part["name"],
            "category": part["category"],
            "specs": part["specs"],
            "description": part["description"],
            "best_similarity_pct": round(final_pct, 1),
            "best_photo_url": best_photo.get("image_path", ""),
            "best_photo_angle": best_photo.get("angle"),
            "thumbnail_urls": thumbnails,
            "total_photos": len(photos),
            "is_high_priority": best_pct > 85.0,
        })

    # Hard rules: sort
    # 1. High priority (>85%) comes first
    # 2. Then by similarity descending
    high_priority = [p for p in part_scores if p["is_high_priority"]]
    normal = [p for p in part_scores if not p["is_high_priority"]]
    high_priority.sort(key=lambda x: x["best_similarity_pct"], reverse=True)
    normal.sort(key=lambda x: x["best_similarity_pct"], reverse=True)
    results = high_priority + normal
    results = results[:top_k]

    msg = f"检索完成，返回{len(results)}条零件结果"
    if degraded and category:
        msg += "（百炼类别未匹配底库，全库检索）"
    elif degraded:
        msg += "（百炼API降级，全库检索）"

    return {"results": results, "query_category": category, "degraded": degraded, "message": msg}


def _update_distance_stats(new_vector: np.ndarray, new_id: int):
    """增量更新L2距离统计量(dist_mean, dist_std)。"""
    existing_ids = list(vector_store._vectors.keys())
    if len(existing_ids) <= 1:
        # Only the new vector itself, can't compute pairwise distances
        part_store.update_stats("dist_mean", 0.0)
        part_store.update_stats("dist_std", 1.0)
        return

    # Compute distances from new vector to all existing vectors
    new_vec = new_vector.astype(np.float32)
    distances = []
    for id_, vec in vector_store._vectors.items():
        if id_ == new_id:
            continue
        d = float(np.linalg.norm(new_vec - vec))
        distances.append(d)

    if not distances:
        return

    # Incremental update: Welford's algorithm style
    stats = part_store.get_stats()
    old_mean = stats.get("dist_mean", 0.0)
    old_std = stats.get("dist_std", 1.0)
    n_old = stats.get("dist_count", 0.0)

    new_dists = np.array(distances)
    n_new = len(new_dists)
    new_mean = float(new_dists.mean())
    new_std = float(new_dists.std()) if n_new > 1 else 0.0

    # Combine old and new distance statistics
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
```

- [ ] **Step 2: Update bailian.py _get_categories**

In `backend/app/services/bailian.py`, change `_get_categories()` to use part_store:

```python
def _get_categories() -> list[str]:
    """延迟获取底库类别列表。"""
    from app.services.pipeline import part_store
    return part_store.get_categories()
```

- [ ] **Step 3: Update VectorStore.add() to accept part_id**

In `backend/app/services/vector_store.py`, modify the `add()` method to accept `part_id` parameter for category_map tracking:

```python
    def add(self, vector: np.ndarray, id: int, category: str, part_id: int = None):
        """动态添加向量到索引。part_id用于category_map关联。"""
        vector = vector.astype(np.float32).reshape(1, -1)
        self._vectors[id] = vector.squeeze()
        if category not in self._category_map:
            self._category_map[category] = set()
        self._category_map[category].add(id)

        self._ensure_index()
        self._index.add_with_ids(vector, np.array([id], dtype=np.int64))
        self.save()
        logger.info(f"向量添加成功: id={id}, category={category}, part_id={part_id}")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/pipeline.py backend/app/services/bailian.py backend/app/services/vector_store.py
git commit -m "feat: rewrite pipeline for part-level architecture with Best-of-Part+boost search"
```

---

### Task 6: Routers — delete learn, expand warehouse, update search, add specs, update health

**Files:**
- Delete: `backend/app/routers/learn.py`
- Rewrite: `backend/app/routers/warehouse.py`
- Modify: `backend/app/routers/search.py`
- Create: `backend/app/routers/specs.py`
- Modify: `backend/app/routers/health.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Delete learn.py**

```bash
rm backend/app/routers/learn.py
```

- [ ] **Step 2: Rewrite warehouse.py with full CRUD**

Replace `backend/app/routers/warehouse.py`:

```python
import io
import os
import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from PIL import Image
from app.models.schemas import (
    WarehouseResponse, PartListItem, PartDetailResponse, PartItem, PhotoItem,
    PartCreate, PartUpdate, SpecKeyItem, SpecKeyCreate
)
from app.services.pipeline import add_part_pipeline, add_photo_pipeline, part_store, vector_store
from app.config import UPLOAD_DIR

router = APIRouter()


@router.get("/parts", response_model=WarehouseResponse)
async def list_parts(category: str | None = Query(None), name: str | None = Query(None)):
    parts = part_store.list_parts(category=category, name=name)
    items = []
    for p in parts:
        photos = part_store.get_photos_for_part(p["id"])
        thumbnails = [ph["image_path"] for ph in photos[:3]]
        items.append(PartListItem(
            id=p["id"], name=p["name"], category=p["category"],
            specs=p["specs"], description=p["description"],
            thumbnail_urls=thumbnails, photo_count=len(photos)
        ))
    return WarehouseResponse(parts=items, total=len(items))


@router.get("/parts/{part_id}", response_model=PartDetailResponse)
async def get_part_detail(part_id: int):
    part = part_store.get_part(part_id)
    if not part:
        raise HTTPException(404, "零件不存在")
    photos = part_store.get_photos_for_part(part_id)
    photo_items = [PhotoItem(**p) for p in photos]
    return PartDetailResponse(part=PartItem(
        id=part["id"], name=part["name"], category=part["category"],
        specs=part["specs"], description=part["description"],
        photos=photo_items
    ))


@router.post("/parts")
async def create_part(
    name: str = Form(...),
    category: str = Form(...),
    specs: str = Form("{}"),
    description: str = Form(None),
    images: list[UploadFile] = File(..., description="零件照片(多张)"),
    angles: list[str] = Form(None, description="角度标签列表(可选)"),
):
    # Parse specs JSON
    import json
    try:
        specs_dict = json.loads(specs)
    except json.JSONDecodeError:
        specs_dict = {}

    # Check unique constraint
    existing = part_store.list_parts(category=category, name=name)
    if existing:
        raise HTTPException(400, f"类别'{category}'下已存在零件'{name}'")

    # Process images
    image_tuples = []
    for i, img_file in enumerate(images):
        image_bytes = await img_file.read()
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Save to disk
        ts = int(time.time() * 1000)
        ext = os.path.splitext(img_file.filename)[1] or ".jpg"
        filename = f"{ts}_{name}-{i}{ext}"
        filepath = UPLOAD_DIR / filename
        pil_image.save(filepath)
        web_path = f"/uploads/{filename}"

        angle = angles[i] if angles and i < len(angles) else None
        image_tuples.append((pil_image, angle, web_path))
        time.sleep(0.001)

    result = add_part_pipeline(name=name, category=category, specs=specs_dict, description=description, images=image_tuples)
    return result


@router.put("/parts/{part_id}")
async def update_part(part_id: int, update: PartUpdate):
    updated = part_store.update_part(
        id=part_id,
        name=update.name,
        category=update.category,
        specs=update.specs,
        description=update.description
    )
    if not updated:
        raise HTTPException(404, "零件不存在")
    # If category changed, rebuild category map
    if update.category:
        from app.services.pipeline import vector_store
        parts = part_store.list_parts()
        all_photos = part_store.get_batch_photos(list(vector_store._vectors.keys()))
        photo_to_part = {p["id"]: p["part_id"] for p in all_photos}
        vector_store.rebuild_category_map(parts, photo_to_part)
    return updated


@router.delete("/parts/{part_id}")
async def delete_part(part_id: int):
    photo_ids = part_store.delete_part(part_id)
    if not photo_ids:
        raise HTTPException(404, "零件不存在")
    vector_store.remove_ids(photo_ids)
    return {"status": "deleted", "part_id": part_id, "removed_photos": len(photo_ids)}


@router.post("/parts/{part_id}/photos")
async def add_photo_to_part(
    part_id: int,
    image: UploadFile = File(...),
    angle: str = Form(None),
):
    part = part_store.get_part(part_id)
    if not part:
        raise HTTPException(404, "零件不存在")

    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    ts = int(time.time() * 1000)
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"{ts}_{part['name']}-add{ext}"
    filepath = UPLOAD_DIR / filename
    pil_image.save(filepath)
    web_path = f"/uploads/{filename}"

    result = add_photo_pipeline(part_id=part_id, image=pil_image, angle=angle, image_path=web_path)
    return result


@router.delete("/parts/{part_id}/photos/{photo_id}")
async def delete_photo(part_id: int, photo_id: int):
    photo = part_store.get_photo(photo_id)
    if not photo:
        raise HTTPException(404, "照片不存在")
    part_store.delete_photo(photo_id)
    vector_store.remove_ids([photo_id])
    return {"status": "deleted", "photo_id": photo_id}
```

- [ ] **Step 3: Update search.py for part-level response**

Replace `backend/app/routers/search.py`:

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
import io
from app.models.schemas import SearchResponse, SearchResult
from app.services.pipeline import search_pipeline

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_item(
    image: UploadFile = File(..., description="待检索图片"),
    top_k: int = Form(default=10, ge=1, le=50, description="返回TopK零件数量"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    result = search_pipeline(image=pil_image, top_k=top_k)

    search_results = [
        SearchResult(
            part_id=r["part_id"],
            name=r["name"],
            category=r["category"],
            specs=r["specs"],
            description=r["description"],
            best_similarity_pct=r["best_similarity_pct"],
            best_photo_url=r["best_photo_url"],
            best_photo_angle=r["best_photo_angle"],
            thumbnail_urls=r["thumbnail_urls"],
            total_photos=r["total_photos"],
        )
        for r in result["results"]
    ]

    return SearchResponse(
        results=search_results,
        query_category=result.get("query_category"),
        degraded=result.get("degraded", False),
        message=result["message"],
    )
```

- [ ] **Step 4: Create specs.py router**

Create `backend/app/routers/specs.py`:

```python
from fastapi import APIRouter, HTTPException
from app.models.schemas import SpecKeyItem, SpecKeyCreate
from app.services.pipeline import part_store

router = APIRouter()


@router.get("/keys", response_model=list[SpecKeyItem])
async def list_spec_keys():
    return part_store.list_spec_keys()


@router.post("/keys", response_model=SpecKeyItem)
async def create_spec_key(data: SpecKeyCreate):
    try:
        return part_store.add_spec_key(key_name=data.key_name, unit=data.unit)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/keys/{key_id}")
async def delete_spec_key(key_id: int):
    part_store.delete_spec_key(key_id)
    return {"status": "deleted"}
```

- [ ] **Step 5: Update health.py**

Replace `backend/app/routers/health.py`:

```python
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.pipeline import part_store, vector_store

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        parts_count=part_store.count_parts(),
        photos_count=part_store.count_photos(),
        faiss_count=vector_store.get_total_count(),
        categories=part_store.get_categories(),
    )
```

- [ ] **Step 6: Update main.py — remove learn, add specs, update lifespan**

In `backend/app/main.py`:
- Remove `from app.routers import learn` and `app.include_router(learn.router, prefix="/api", tags=["学习端"])`
- Add `from app.routers import specs` and `app.include_router(specs.router, prefix="/api/specs", tags=["规格字典"])`
- Update lifespan: use `part_store` instead of `metadata_store`, call `run_migration()`, rebuild category map from parts+photos

- [ ] **Step 7: Commit**

```bash
git add -A backend/app/routers/ backend/app/main.py
git commit -m "feat: delete learn router, add warehouse CRUD/specs/search part-level/health update"
```

---

### Task 7: Frontend — router, App.vue, stores

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/stores/system.js`
- Create: `frontend/src/stores/warehouse.js`

- [ ] **Step 1: Update router — remove learn route**

Replace `frontend/src/router/index.js`:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/SearchView.vue'
import WarehouseView from '../views/WarehouseView.vue'

const routes = [
  { path: '/', redirect: '/warehouse' },
  { path: '/search', name: 'search', component: SearchView },
  { path: '/warehouse', name: 'warehouse', component: WarehouseView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 2: Update App.vue — remove learn nav**

In `frontend/src/App.vue`, remove the learn nav link and update default route. The nav section becomes two links: Search + Warehouse. Update `dbCount` to `partsCount`.

- [ ] **Step 3: Update system.js store — new health fields**

Replace `frontend/src/stores/system.js`:

```javascript
import { defineStore } from 'pinia'
import api from '../api'

export const useSystemStore = defineStore('system', {
  state: () => ({
    partsCount: 0,
    photosCount: 0,
    categories: [],
    systemOnline: false,
    isScanning: false,
  }),
  actions: {
    async fetchHealth() {
      try {
        const res = await api.get('/health')
        this.partsCount = res.data.parts_count
        this.photosCount = res.data.photos_count
        this.categories = res.data.categories
        this.systemOnline = true
      } catch {
        this.systemOnline = false
      }
    },
  },
})
```

- [ ] **Step 4: Create warehouse.js store**

Create `frontend/src/stores/warehouse.js`:

```javascript
import { defineStore } from 'pinia'
import api from '../api'

export const useWarehouseStore = defineStore('warehouse', {
  state: () => ({
    parts: [],
    total: 0,
    currentPart: null,
    specKeys: [],
    isCreating: false,
    filterCategory: null,
    filterName: '',
  }),
  actions: {
    async fetchParts() {
      const params = {}
      if (this.filterCategory) params.category = this.filterCategory
      if (this.filterName) params.name = this.filterName
      const res = await api.get('/warehouse/parts', { params })
      this.parts = res.data.parts
      this.total = res.data.total
    },
    async fetchPartDetail(partId) {
      const res = await api.get(`/warehouse/parts/${partId}`)
      this.currentPart = res.data.part
    },
    async fetchSpecKeys() {
      const res = await api.get('/specs/keys')
      this.specKeys = res.data
    },
    async deletePart(partId) {
      await api.delete(`/warehouse/parts/${partId}`)
      await this.fetchParts()
    },
    async deletePhoto(partId, photoId) {
      await api.delete(`/warehouse/parts/${partId}/photos/${photoId}`)
      await this.fetchPartDetail(partId)
    },
    async updatePart(partId, data) {
      await api.put(`/warehouse/parts/${partId}`, data)
      await this.fetchPartDetail(partId)
      await this.fetchParts()
    },
    async addPhoto(partId, formData) {
      await api.post(`/warehouse/parts/${partId}/photos`, formData)
      await this.fetchPartDetail(partId)
    },
  },
})
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/router/index.js frontend/src/App.vue frontend/src/stores/system.js frontend/src/stores/warehouse.js
git commit -m "feat: update frontend router/stores/App.vue for two-page architecture"
```

---

### Task 8: Frontend — WarehouseView.vue rewrite

**Files:**
- Delete: `frontend/src/views/LearnView.vue`
- Rewrite: `frontend/src/views/WarehouseView.vue`

- [ ] **Step 1: Delete LearnView.vue**

```bash
rm frontend/src/views/LearnView.vue
```

- [ ] **Step 2: Rewrite WarehouseView.vue**

Write `frontend/src/views/WarehouseView.vue` with:
- Category filter tabs + name search input
- Part list: each part = one row with name + category badge + 3 thumbnails + spec summary
- Click row → expand detail panel: all photos (with angle labels), specs key-value table, description, CRUD buttons (delete part, delete photo, edit specs, add photo)
- "新增零件" button → modal form: category dropdown + name input + specs key-value rows + description + multi-photo upload with angle labels
- Spec keys loaded from `/specs/keys` for dropdown

This is the largest frontend change. The full Vue component will be ~250 lines using `<script setup>` Composition API.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/WarehouseView.vue
git rm frontend/src/views/LearnView.vue
git commit -m "feat: rewrite WarehouseView with CRUD+add-part, delete LearnView"
```

---

### Task 9: Frontend — SearchView.vue rewrite for part-level results

**Files:**
- Rewrite: `frontend/src/views/SearchView.vue`

- [ ] **Step 1: Rewrite SearchView.vue**

Write `frontend/src/views/SearchView.vue` with:
- Query upload + top_k input (same as before)
- Results: each result = one part row showing name + category + similarity percentage (direct from API, e.g. "78.3%") + 3 thumbnails
- Click row → expand detail: all photos + angle labels + specs + description
- Remove `similarityPercent()` and `formatSimilarity()` — use `best_similarity_pct` directly from API
- Keep 百炼 category badge and degraded indicator

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/SearchView.vue
git commit -m "feat: rewrite SearchView for part-level results with percentage similarity"
```

---

### Task 10: Frontend CSS — remove learn styles, add CRUD styles

**Files:**
- Modify: `frontend/src/assets/styles/main.css`

- [ ] **Step 1: Update main.css**

Remove `.learn-layout` grid and all learn-specific upload/preview classes. Add:
- `.part-row` — horizontal layout for one part in list
- `.part-thumbnails` — 3 thumbnail images side by side
- `.part-detail` — expanded detail panel
- `.specs-table` — key-value table for specs
- `.crud-bar` — action buttons row (delete, edit, add)
- `.create-part-modal` — modal overlay for add-part form
- `.spec-row` — dynamic key-value input row in form
- `.angle-input` — angle label input per photo

- [ ] **Step 2: Commit**

```bash
git add frontend/src/assets/styles/main.css
git commit -m "feat: update CSS — remove learn styles, add part/CRUD styles"
```

---

### Task 11: Rebuild FAISS index and compute initial stats

**Files:**
- Modify: `backend/rebuild_faiss.py`

- [ ] **Step 1: Update rebuild_faiss.py for part-level data**

Update `backend/rebuild_faiss.py` to:
- Read from parts+photos tables instead of metadata
- Store photo.id as FAISS vector ID (same as before)
- Add part_id info to category_map
- Compute and store initial dist_mean and dist_std in stats_meta table

- [ ] **Step 2: Run rebuild and verify**

```bash
cd backend && python rebuild_faiss.py
```

Expected: 24 vectors, correct part grouping, stats_meta populated with dist_mean and dist_std.

- [ ] **Step 3: Start server and test migration + search**

```bash
cd backend && python run.py
```

Test: `curl http://localhost:8000/api/health` — should show parts_count, photos_count, faiss_count.

Test search: `curl -X POST http://localhost:8000/api/search/query -F "image=@data/uploads/xxx.jpg" -F "top_k=3"` — should return part-level results with percentage similarity.

Test warehouse: `curl http://localhost:8000/api/warehouse/parts` — should return part list with thumbnails.

- [ ] **Step 4: Commit**

```bash
git add backend/rebuild_faiss.py
git commit -m "feat: update rebuild script for part-level data + stats computation"
```

---

### Task 12: Integration test — full flow verification

**Files:**
- No code changes, just testing

- [ ] **Step 1: Test warehouse CRUD flow**

1. `GET /api/warehouse/parts` — list all parts
2. `POST /api/warehouse/parts` — create a new part with 3 photos
3. `GET /api/warehouse/parts/{id}` — view part detail
4. `PUT /api/warehouse/parts/{id}` — update specs
5. `POST /api/warehouse/parts/{id}/photos` — add a photo
6. `DELETE /api/warehouse/parts/{id}/photos/{photo_id}` — delete a photo
7. `DELETE /api/warehouse/parts/{id}` — delete entire part

- [ ] **Step 2: Test search flow**

1. Upload a query image → should return top_k parts with percentage similarity
2. Verify Best-of-Part: same part's best photo is used as similarity
3. Verify boost: parts with multiple close matches get slight boost
4. Verify threshold rule: >85% parts appear first
5. Verify degraded mode: 百炼 API failure → full-library search

- [ ] **Step 3: Test frontend in browser**

1. Open `/warehouse` — should show parts list with thumbnails
2. Click a part — should expand detail with photos, specs, CRUD buttons
3. Click "新增零件" — should show form with category, name, specs key-value, photo upload
4. Open `/search` — should show query upload and search results as part rows
5. Click a result part — should expand detail

- [ ] **Step 4: Commit (no changes, just verification)**