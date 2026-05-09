import logging
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from app.config import DINOV2_MODEL_NAME, DINOV2_FEATURE_DIM

logger = logging.getLogger(__name__)

_model = None
_transform = None


def _load_model():
    global _model, _transform
    if _model is None:
        logger.info(f"加载DINOv2模型: {DINOV2_MODEL_NAME}")
        _model = torch.hub.load("facebookresearch/dinov2", DINOV2_MODEL_NAME)
        _model.eval()
        _transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return _model, _transform


def extract_features(image: Image.Image) -> np.ndarray:
    """提取图像特征向量(dinov2_vitl14, dim=1024)。"""
    model, transform = _load_model()
    img_tensor = transform(image.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        features = model(img_tensor)
    features_np = features.squeeze(0).cpu().numpy()
    assert features_np.shape == (DINOV2_FEATURE_DIM,), f"特征维度异常: {features_np.shape}"
    return features_np.astype(np.float32)