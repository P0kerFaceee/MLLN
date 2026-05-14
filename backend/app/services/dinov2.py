import logging
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModel, AutoImageProcessor
from app.config import DINOV2_MODEL_PATH

logger = logging.getLogger(__name__)

_model = None
_transform = None


def _load_model(max_retries: int = 3):
    global _model, _transform
    if _model is None:
        logger.info(f"加载本地DINOv2模型: {DINOV2_MODEL_PATH}")
        
        # 检查模型路径是否存在
        if not DINOV2_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"DINOv2模型路径不存在: {DINOV2_MODEL_PATH}\n"
                f"请检查.env文件中的DINOV2_MODEL_PATH配置是否正确"
            )

        # 加载模型
        _model = AutoModel.from_pretrained(str(DINOV2_MODEL_PATH))
        _model.eval()

        # 加载图像处理器
        processor = AutoImageProcessor.from_pretrained(str(DINOV2_MODEL_PATH))

        # 创建转换函数
        def transform(image):
            inputs = processor(images=image.convert("RGB"), return_tensors="pt")
            return inputs["pixel_values"].squeeze(0)

        _transform = transform

    return _model, _transform


def extract_features(image: Image.Image) -> np.ndarray:
    """提取图像特征向量(dinov2_vitl14, dim=1024)。"""
    model, transform = _load_model()
    img_tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        outputs = model(img_tensor)
        # 获取最后一层隐藏状态的平均值作为特征向量
        features = outputs.last_hidden_state.mean(dim=1)
    features_np = features.squeeze(0).cpu().numpy()
    assert features_np.shape == (1024,), f"特征维度异常: {features_np.shape}"
    return features_np.astype(np.float32)