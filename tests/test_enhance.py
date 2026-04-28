import numpy as np
from PIL import Image
from app.services.enhance import enhance_image


def test_enhance_normal_image():
    img = Image.fromarray(np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8))
    result = enhance_image(img)
    assert isinstance(result, Image.Image)
    assert result.size == img.size


def test_enhance_returns_original_on_failure():
    img = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
    result = enhance_image(img)
    assert isinstance(result, Image.Image)
    assert result.size == img.size