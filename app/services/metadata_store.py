import sqlite3
import logging
from app.config import DB_PATH

logger = logging.getLogger(__name__)


class MetadataStore:
    """SQLite元数据存储：图文信息关联。"""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                specification TEXT NOT NULL,
                description TEXT,
                image_path TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def add(self, id: int, category: str, specification: str, description: str | None, image_path: str, status: str = "active"):
        self._conn.execute(
            "INSERT INTO metadata (id, category, specification, description, image_path, status) VALUES (?, ?, ?, ?, ?, ?)",
            (id, category, specification, description, image_path, status),
        )
        self._conn.commit()
        logger.info(f"元数据写入成功: id={id}, category={category}")

    def get(self, id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM metadata WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_batch(self, ids: list[int]) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM metadata WHERE id IN ({})".format(",".join(map(str, ids)))
        ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM metadata").fetchone()
        return row[0]

    def close(self):
        self._conn.close()