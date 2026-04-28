from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
from app.services.bailian import classify_category


def test_classify_category_success():
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "螺栓"

    with patch("app.services.bailian._call_api", return_value=mock_response):
        result = classify_category(img)
        assert result == "螺栓"


def test_classify_category_api_failure_returns_none():
    img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))

    with patch("app.services.bailian._call_api", side_effect=Exception("API timeout")):
        result = classify_category(img)
        assert result is None