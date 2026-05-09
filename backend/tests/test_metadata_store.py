import os
from app.services.metadata_store import MetadataStore
from app.config import DB_PATH


def _get_test_db_path():
    return str(DB_PATH).replace("metadata.db", "test_metadata.db")


def test_add_and_get():
    db_path = _get_test_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    store = MetadataStore(db_path=db_path)
    store.add(id=1, category="螺栓", specification="M10x30", description="六角头螺栓", image_path="/uploads/bolt1.png")
    record = store.get(1)
    assert record is not None
    assert record["category"] == "螺栓"
    assert record["specification"] == "M10x30"
    assert record["description"] == "六角头螺栓"
    store.close()
    os.remove(db_path)


def test_get_multiple():
    db_path = _get_test_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    store = MetadataStore(db_path=db_path)
    store.add(id=2, category="齿轮", specification="Z20", description="直齿轮", image_path="/uploads/gear1.png")
    store.add(id=3, category="齿轮", specification="Z30", description="斜齿轮", image_path="/uploads/gear2.png")
    records = store.get_batch([2, 3])
    assert len(records) == 2
    assert all(r["category"] == "齿轮" for r in records)
    store.close()
    os.remove(db_path)


def test_get_nonexistent():
    db_path = _get_test_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    store = MetadataStore(db_path=db_path)
    result = store.get(999)
    assert result is None
    store.close()
    os.remove(db_path)


def test_count():
    db_path = _get_test_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    store = MetadataStore(db_path=db_path)
    count = store.count()
    assert isinstance(count, int)
    store.close()
    os.remove(db_path)