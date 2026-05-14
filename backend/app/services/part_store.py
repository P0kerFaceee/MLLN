from typing import Optional, List, Dict
import logging
import sqlite3
import json
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

    def add_part(self, id: int, name: str, category: str, specs: Optional[Dict] = None, description: Optional[str] = None) -> Dict:
        specs_json = json.dumps(specs or {}, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO parts (id, name, category, specs, description) VALUES (?, ?, ?, ?, ?)",
            (id, name, category, specs_json, description)
        )
        self._conn.commit()
        return {"id": id, "name": name, "category": category, "specs": specs or {}, "description": description}

    def get_part(self, id: int) -> Optional[Dict]:
        row = self._conn.execute("SELECT * FROM parts WHERE id = ? AND status = 'active'", (id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["specs"] = json.loads(result["specs"])
        return result

    def list_parts(self, category: Optional[str] = None, name: Optional[str] = None) -> List[Dict]:
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

    def update_part(self, id: int, name: Optional[str] = None, category: Optional[str] = None, specs: Optional[Dict] = None, description: Optional[str] = None):
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

    def delete_part(self, id: int) -> List[int]:
        photo_ids = [r["id"] for r in self._conn.execute("SELECT id FROM photos WHERE part_id = ? AND status = 'active'", (id,)).fetchall()]
        self._conn.execute("UPDATE parts SET status = 'deleted' WHERE id = ?", (id,))
        self._conn.execute("UPDATE photos SET status = 'deleted' WHERE part_id = ?", (id,))
        self._conn.commit()
        return photo_ids

    def count_parts(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM parts WHERE status = 'active'").fetchone()
        return row["cnt"]

    def get_categories(self) -> List[str]:
        rows = self._conn.execute("SELECT DISTINCT category FROM parts WHERE status = 'active' ORDER BY category").fetchall()
        return [r["category"] for r in rows]

    def add_photo(self, id: int, part_id: int, image_path: str, angle: Optional[str] = None) -> Dict:
        self._conn.execute(
            "INSERT INTO photos (id, part_id, image_path, angle) VALUES (?, ?, ?, ?)",
            (id, part_id, image_path, angle)
        )
        self._conn.commit()
        return {"id": id, "part_id": part_id, "image_path": image_path, "angle": angle}

    def get_photos_for_part(self, part_id: int) -> List[Dict]:
        rows = self._conn.execute("SELECT * FROM photos WHERE part_id = ? AND status = 'active' ORDER BY id", (part_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_photo(self, id: int) -> Optional[Dict]:
        row = self._conn.execute("SELECT * FROM photos WHERE id = ? AND status = 'active'", (id,)).fetchone()
        return dict(row) if row else None

    def delete_photo(self, id: int):
        self._conn.execute("UPDATE photos SET status = 'deleted' WHERE id = ?", (id,))
        self._conn.commit()

    def count_photos(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM photos WHERE status = 'active'").fetchone()
        return row["cnt"]

    def add_spec_key(self, key_name: str, unit: Optional[str] = None) -> Dict:
        self._conn.execute("INSERT INTO spec_keys (key_name, unit) VALUES (?, ?)", (key_name, unit))
        self._conn.commit()
        return {"key_name": key_name, "unit": unit}

    def list_spec_keys(self) -> List[Dict]:
        rows = self._conn.execute("SELECT * FROM spec_keys ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def delete_spec_key(self, id: int):
        self._conn.execute("DELETE FROM spec_keys WHERE id = ?", (id,))
        self._conn.commit()

    def get_stats(self) -> Dict:
        rows = self._conn.execute("SELECT key, value FROM stats_meta").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def update_stats(self, key: str, value: float):
        self._conn.execute("INSERT OR REPLACE INTO stats_meta (key, value) VALUES (?, ?)", (key, value))
        self._conn.commit()

    def get_batch_photos(self, ids: List[int]) -> List[Dict]:
        rows = self._conn.execute(
            f"SELECT * FROM photos WHERE id IN ({','.join(map(str, ids))}) AND status = 'active'"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_photo_to_part_map(self, photo_ids: List[int]) -> Dict[int, int]:
        """返回 photo_id → part_id 的映射。"""
        rows = self._conn.execute(
            f"SELECT id, part_id FROM photos WHERE id IN ({','.join(map(str, photo_ids))}) AND status = 'active'"
        ).fetchall()
        return {r["id"]: r["part_id"] for r in rows}

    def close(self):
        self._conn.close()