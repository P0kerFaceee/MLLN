import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件（仅本地，不入git）
load_dotenv()

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
DINOV2_MODEL_PATH = BASE_DIR / os.getenv("DINOV2_MODEL_PATH", "/app/model/DINOv2-large").lstrip("/")

# FAISS
FAISS_NLIST = 100
FAISS_NPROBE = 10
FAISS_DEFAULT_TOP_K = 10

# Bailian API
BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY", "sk-aa0794e0c6734d52bc9d2ce315c53208")
BAILIAN_BASE_URL = os.getenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
BAILIAN_MODEL_NAME = os.getenv("BAILIAN_MODEL_NAME", "qwen3.6-plus")
BAILIAN_TIMEOUT = float(os.getenv("BAILIAN_TIMEOUT", "10.0"))