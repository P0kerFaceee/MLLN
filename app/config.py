from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "db" / "metadata.db"
FAISS_INDEX_PATH = DATA_DIR / "faiss" / "index.faiss"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

# YOLO
YOLO_MODEL_NAME = "yolov8n.pt"

# DINOv2
DINOV2_MODEL_NAME = "dinov2_vitl14"
DINOV2_FEATURE_DIM = 1024

# FAISS
FAISS_NLIST = 100
FAISS_NPROBE = 10
FAISS_DEFAULT_TOP_K = 10

# Bailian API
BAILIAN_API_KEY = ""
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
BAILIAN_MODEL_NAME = "qwen-vl-max-latest"
BAILIAN_TIMEOUT = 10.0