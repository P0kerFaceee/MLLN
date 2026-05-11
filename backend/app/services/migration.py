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
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "metadata" not in tables:
        conn.close()
        return False
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

    rows = conn.execute("SELECT * FROM metadata WHERE status = 'active'").fetchall()
    logger.info(f"迁移: {len(rows)} 条 metadata 记录")

    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (row["category"], row["specification"])
        groups.setdefault(key, []).append(dict(row))

    for (category, specification), items in groups.items():
        part_id = min(item["id"] for item in items)
        try:
            conn.execute(
                "INSERT INTO parts (id, name, category, specs, description) VALUES (?, ?, ?, ?, ?)",
                (part_id, specification, category, json.dumps({}, ensure_ascii=False), items[0]["description"])
            )
        except sqlite3.IntegrityError:
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
    conn.close()