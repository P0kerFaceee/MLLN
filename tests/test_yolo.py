from PIL import Image
import numpy as np
from app.services.yolo import yolo_detect_and_crop


def test_yolo_detect_returns_crop_or_none():
    arr = np.ones((640, 640, 3), dtype=np.uint8) * 255
    arr[200:400, 200:400] = 0
    img = Image.fromarray(arr)
    result = yolo_detect_and_crop(img)
    # YOLO可能检测不到合成图中的目标，此时返回None是正常的
    assert result is None or isinstance(result, tuple)
    if result is not None:
        crop, boxes = result
        assert isinstance(crop, Image.Image)
        assert isinstance(boxes, list)