from unittest.mock import patch

import numpy as np
from PIL import Image

from app.config import DINOV2_FEATURE_DIM
from app.services.pipeline import search_pipeline


def _make_image():
    return Image.fromarray(np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8))


def _mock_part_store(mock_store):
    mock_store.get_photo_to_part_map.return_value = {101: 1, 102: 1}
    mock_store.get_batch_photos.return_value = [
        {"id": 101, "part_id": 1, "image_path": "/uploads/b1.png", "angle": "正面"},
        {"id": 102, "part_id": 1, "image_path": "/uploads/b2.png", "angle": "侧面"},
    ]
    mock_store.get_part.return_value = {
        "id": 1,
        "name": "M10x30",
        "category": "螺栓",
        "specs": {"长度": "30mm"},
        "description": "",
    }
    mock_store.get_photos_for_part.return_value = mock_store.get_batch_photos.return_value


def test_search_pipeline_uses_frontend_category_filter():
    img = _make_image()
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)

    with patch("app.services.pipeline.enhance_image", return_value=img), \
         patch("app.services.pipeline.extract_features", return_value=mock_vec), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.part_store") as mock_ps:
        mock_vs.get_categories.return_value = ["螺栓"]
        mock_vs.search.return_value = ([101, 102], [0.1, 0.2])
        _mock_part_store(mock_ps)

        result = search_pipeline(image=img, top_k=10, category="螺栓", specs={"长度": "30mm"})

        mock_vs.search.assert_called_once()
        assert mock_vs.search.call_args.kwargs["category"] == "螺栓"
        assert result["degraded"] is False
        assert result["query_category"] == "螺栓"
        assert len(result["results"]) == 1


def test_search_pipeline_without_valid_category_uses_full_search():
    img = _make_image()
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)

    with patch("app.services.pipeline.enhance_image", return_value=img), \
         patch("app.services.pipeline.extract_features", return_value=mock_vec), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.part_store") as mock_ps:
        mock_vs.get_categories.return_value = ["螺栓"]
        mock_vs.search.return_value = ([101], [0.5])
        _mock_part_store(mock_ps)

        result = search_pipeline(image=img, top_k=10, category="未知类别")

        assert mock_vs.search.call_args.kwargs["category"] is None
        assert result["degraded"] is True
        assert result["query_category"] == "未知类别"
