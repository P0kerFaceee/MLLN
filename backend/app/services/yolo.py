import logging
from PIL import Image
from ultralytics import YOLO
from app.config import YOLO_MODEL_NAME

logger = logging.getLogger(__name__)

_model = None


def _load_model() -> YOLO:
    global _model
    if _model is None:
        logger.info(f"加载YOLO模型: {YOLO_MODEL_NAME}")
        _model = YOLO(YOLO_MODEL_NAME)
    return _model


def yolo_detect_and_crop(image: Image.Image) -> tuple[Image.Image, list] | None:
    """YOLO目标检测+裁剪。返回(裁剪子图, 检测框列表)或None（未检测到目标）。"""
    model = _load_model()
    results = model(image, verbose=False)

    if not results or len(results[0].boxes) == 0:
        logger.warning("YOLO未检测到目标区域")
        return None

    boxes = results[0].boxes
    best_idx = boxes.conf.argmax().item()
    best_box = boxes.xyxy[best_idx].cpu().numpy()

    x1, y1, x2, y2 = map(int, best_box)
    cropped = image.crop((x1, y1, x2, y2))

    all_boxes = boxes.xyxy.cpu().numpy().tolist()
    return cropped, all_boxes