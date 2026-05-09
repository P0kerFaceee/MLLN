from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
from app.services.pipeline import learn_pipeline, search_pipeline
from app.config import DINOV2_FEATURE_DIM


def test_learn_pipeline_success():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))

    with patch("app.services.pipeline.enhance_image", return_value=img), \
         patch("app.services.pipeline.extract_features", return_value=np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.metadata_store") as mock_ms:

        result = learn_pipeline(image=img, category="螺栓", specification="M10x30", description="六角头螺栓", image_path="/uploads/bolt1.png")
        assert result["status"] == "success"
        assert result["id"] > 0
        mock_vs.add.assert_called_once()
        mock_ms.add.assert_called_once()


def test_search_pipeline_success():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    mock_search_result = ([1, 2, 3], [0.1, 0.2, 0.3])

    with patch("app.services.pipeline.classify_category", return_value="螺栓"), \
         patch("app.services.pipeline.extract_features", return_value=mock_vec), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.metadata_store") as mock_ms:

        mock_vs.search.return_value = mock_search_result
        mock_ms.get_batch.return_value = [
            {"id": 1, "category": "螺栓", "specification": "M10x30", "description": "", "image_path": "/uploads/b1.png"},
            {"id": 2, "category": "螺栓", "specification": "M12x40", "description": "", "image_path": "/uploads/b2.png"},
            {"id": 3, "category": "螺栓", "specification": "M8x20", "description": "", "image_path": "/uploads/b3.png"},
        ]

        result = search_pipeline(image=img, top_k=10)
        assert result["degraded"] is False
        assert result["query_category"] == "螺栓"
        assert len(result["results"]) == 3


def test_search_pipeline_bailian_degraded():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)

    with patch("app.services.pipeline.classify_category", return_value=None), \
         patch("app.services.pipeline.extract_features", return_value=mock_vec), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.metadata_store") as mock_ms:

        mock_vs.search.return_value = ([1], [0.5])
        mock_ms.get_batch.return_value = [{"id": 1, "category": "螺栓", "specification": "M10", "description": "", "image_path": "/u/b1.png"}]

        result = search_pipeline(image=img, top_k=10)
        assert result["degraded"] is True
        assert result["query_category"] is None