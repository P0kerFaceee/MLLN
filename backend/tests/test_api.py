import io
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _make_test_image_bytes():
    arr = np.random.randint(50, 200, (128, 128, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["parts_count"], int)
    assert isinstance(data["photos_count"], int)
    assert isinstance(data["faiss_count"], int)
    assert isinstance(data["categories"], list)


def test_search_accepts_frontend_category_and_specs():
    with patch("app.routers.search.search_pipeline") as mock_search:
        mock_search.return_value = {
            "results": [],
            "query_category": "螺栓",
            "degraded": False,
            "message": "检索完成，返回0条零件结果",
        }

        response = client.post(
            "/api/search/query",
            files={"image": ("query.png", _make_test_image_bytes(), "image/png")},
            data={"top_k": "5", "category": "螺栓", "specs": '{"长度":"30mm"}'},
        )

    assert response.status_code == 200
    mock_search.assert_called_once()
    assert mock_search.call_args.kwargs["category"] == "螺栓"
    assert mock_search.call_args.kwargs["specs"] == {"长度": "30mm"}
