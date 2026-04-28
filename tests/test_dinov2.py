from PIL import Image
import numpy as np
from app.services.dinov2 import extract_features
from app.config import DINOV2_FEATURE_DIM


def test_extract_features_dimension():
    img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    features = extract_features(img)
    assert features.shape == (DINOV2_FEATURE_DIM,)
    assert features.dtype.name.startswith("float")


def test_extract_features_same_image_consistent():
    img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    f1 = extract_features(img)
    f2 = extract_features(img)
    cos_sim = np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))
    assert cos_sim > 0.99