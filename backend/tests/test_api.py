from fastapi.testclient import TestClient
from app.main import app
import io
import numpy as np
from PIL import Image

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["db_count"], int)
    assert isinstance(data["faiss_count"], int)


def _make_test_image_bytes():
    arr = np.random.randint(50, 200, (640, 640, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_learn_and_search_flow():
    img_buf = _make_test_image_bytes()
    learn_response = client.post(
        "/api/learn/upload",
        files={"image": ("test.png", img_buf, "image/png")},
        data={"category": "test_cat", "specification": "test_spec", "description": "test_desc"},
    )
    assert learn_response.status_code == 200
    learn_data = learn_response.json()
    assert learn_data["status"] in ["success", "pending_review"]

    img_buf2 = _make_test_image_bytes()
    search_response = client.post(
        "/api/search/query",
        files={"image": ("query.png", img_buf2, "image/png")},
        data={"top_k": "5"},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert isinstance(search_data["results"], list)