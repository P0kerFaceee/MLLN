# 工业仓库物流识别系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建公司级工业仓库物流识别系统，支持学习端底库构建和使用端实时检索（<5s）

**Architecture:** 串行管道设计，学习端（图像增强→YOLO→DINOv2→FAISS写入）构建底库，使用端（YOLO→百炼API类别预过滤→DINOv2→FAISS检索）实时检索。FAISS与SQLite解耦，FAISS只存向量+ID，SQLite存完整图文元数据。

**Tech Stack:** Python 3.14, FastAPI, ultralytics (YOLOv8), torch (DINOv2 ViT-L/14), faiss-cpu, SQLite,阿里百炼API

---

## File Structure

```
D:/planforme/
├── app/
│   ├── main.py                    # FastAPI入口，路由注册
│   ├── config.py                  # 配置管理（模型路径、API密钥、FAISS参数）
│   ├── models/
│   │   └── schemas.py             # Pydantic请求/响应数据模型
│   ├── services/
│   │   ├── enhance.py             # 图像增强模块
│   │   ├── yolo.py                # YOLO推理模块（目标检测+裁剪）
│   │   ├── dinov2.py              # DINOv2特征提取模块(dinov2_vitl14)
│   │   ├── bailian.py             # 阿里百炼API调用模块
│   │   ├── vector_store.py        # FAISS向量库模块（索引管理+检索）
│   │   ├── metadata_store.py      # SQLite元数据存储模块
│   │   └── pipeline.py            # 学习端+使用端管道编排
│   └── routers/
│       ├── learn.py               # 学习端API路由（上传+入库）
│       ├── search.py              # 使用端API路由（检索）
│       └── health.py              # 健康检查路由
├── data/
│   ├── db/
│   │   └── metadata.db            # SQLite数据库文件（运行时创建）
│   └── faiss/
│   │   └── index.faiss            # FAISS索引文件（运行时创建）
│   └── uploads/                   # 上传图片存储目录
├── tests/
│   ├── test_enhance.py
│   ├── test_yolo.py
│   ├── test_dinov2.py
│   ├── test_bailian.py
│   ├── test_vector_store.py
│   ├── test_metadata_store.py
│   ├── test_pipeline.py
│   └── test_api.py
├── requirements.txt
├── run.py                          # 启动脚本
docs/
├── superpowers/
│   ├── specs/
│   │   └── 2026-04-28-industrial-warehouse-recognition-system-design.md
│   ├── plans/
│   │   └── 2026-04-28-industrial-warehouse-recognition-system.md
```

---

### Task 1: 项目初始化与依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `app/config.py`
- Create: `app/main.py`
- Create: `run.py`
- Create: `data/uploads/` (directory)
- Create: `data/db/` (directory)
- Create: `data/faiss/` (directory)

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.115.12
uvicorn==0.34.2
python-multipart==0.0.20
ultralytics==8.3.144
torch==2.7.0
torchvision==0.22.0
faiss-cpu==1.11.0
numpy==2.2.6
pillow==11.2.1
openai==1.82.0
sqlite3
pydantic==2.11.3
httpx==0.28.1
```

- [ ] **Step 2: 创建 app/config.py**

```python
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
```

- [ ] **Step 3: 创建 app/main.py**

```python
from fastapi import FastAPI
from app.routers import learn, search, health

app = FastAPI(title="工业仓库物流识别系统", version="1.0.0")

app.include_router(health.router)
app.include_router(learn.router, prefix="/api/learn", tags=["学习端"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])
```

- [ ] **Step 4: 创建 run.py**

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 5: 创建目录结构和 __init__.py 文件**

创建 `app/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/routers/__init__.py`, `tests/__init__.py` — 均为空文件。

```bash
mkdir -p data/uploads data/db data/faiss
touch app/__init__.py app/models/__init__.py app/services/__init__.py app/routers/__init__.py tests/__init__.py
```

- [ ] **Step 6: 安装依赖**

```bash
pip install -r requirements.txt
```

- [ ] **Step 7: 验证FastAPI能启动**

```bash
python run.py
```

浏览器访问 `http://localhost:8000/docs` 确认Swagger UI出现。然后停止服务。

- [ ] **Step 8: Commit**

```bash
git add requirements.txt app/config.py app/main.py run.py app/__init__.py app/models/__init__.py app/services/__init__.py app/routers/__init__.py tests/__init__.py
git commit -m "feat: project init with FastAPI scaffold and config"
```

---

### Task 2: Pydantic 数据模型定义

**Files:**
- Create: `app/models/schemas.py`

- [ ] **Step 1: 创建 app/models/schemas.py**

```python
from pydantic import BaseModel, Field
from typing import Optional


class LearnRequest(BaseModel):
    category: str = Field(..., description="零件类别")
    specification: str = Field(..., description="零件规格")
    description: Optional[str] = Field(None, description="零件描述信息")


class LearnResponse(BaseModel):
    id: int
    category: str
    specification: str
    description: Optional[str]
    status: str = Field(..., description="处理状态: success / pending_review / pending_complete")
    message: str


class SearchRequest(BaseModel):
    top_k: int = Field(default=10, description="返回TopK结果数量")


class SearchResult(BaseModel):
    id: int
    category: str
    specification: str
    description: Optional[str]
    similarity: float
    image_url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_category: Optional[str] = Field(None, description="百炼API判断的类别，降级时为None")
    degraded: bool = Field(default=False, description="是否为降级模式（百炼API不可用）")
    message: str


class HealthResponse(BaseModel):
    status: str
    db_count: int
    faiss_count: int
    categories: list[str]
```

- [ ] **Step 2: Commit**

```bash
git add app/models/schemas.py
git commit -m "feat: add Pydantic request/response schemas"
```

---

### Task 3: 图像增强模块

**Files:**
- Create: `app/services/enhance.py`
- Create: `tests/test_enhance.py`

- [ ] **Step 1: 编写 test_enhance.py**

```python
import numpy as np
from PIL import Image
from app.services.enhance import enhance_image


def test_enhance_normal_image():
    img = Image.fromarray(np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8))
    result = enhance_image(img)
    assert isinstance(result, Image.Image)
    assert result.size == img.size


def test_enhance_returns_original_on_failure():
    # 传入一个极端暗图，增强应仍能返回有效图片（不崩溃）
    img = Image.fromarray(np.zeros((10, 10, 3), dtype=np.uint8))
    result = enhance_image(img)
    assert isinstance(result, Image.Image)
    assert result.size == img.size
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_enhance.py -v
```

Expected: FAIL — `enhance_image` 未定义

- [ ] **Step 3: 实现 app/services/enhance.py**

```python
import logging
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


def enhance_image(image: Image.Image) -> Image.Image:
    """图像增强：去噪、对比度调整、光照校正。增强失败时返回原始图片。"""
    try:
        # 去噪
        denoised = image.filter(ImageFilter.MedianFilter(size=3))
        # 对比度增强
        contrast = ImageEnhance.Contrast(denoised)
        enhanced = contrast.enhance(1.5)
        # 亮度校正
        brightness = ImageEnhance.Brightness(enhanced)
        enhanced = brightness.enhance(1.2)
        return enhanced
    except Exception as e:
        logger.warning(f"图像增强失败，返回原始图片: {e}")
        return image
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_enhance.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/enhance.py tests/test_enhance.py
git commit -m "feat: add image enhancement module"
```

---

### Task 4: YOLO推理模块

**Files:**
- Create: `app/services/yolo.py`
- Create: `tests/test_yolo.py`

- [ ] **Step 1: 编写 test_yolo.py**

```python
from PIL import Image
import numpy as np
from app.services.yolo import yolo_detect_and_crop


def test_yolo_detect_returns_crop():
    # 创建一张带有明显矩形区域的合成图（白色背景+黑色方块）
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_yolo.py -v
```

Expected: FAIL — `yolo_detect_and_crop` 未定义

- [ ] **Step 3: 实现 app/services/yolo.py**

```python
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

    # 取置信度最高的检测框
    boxes = results[0].boxes
    best_idx = boxes.conf.argmax().item()
    best_box = boxes.xyxy[best_idx].cpu().numpy()

    x1, y1, x2, y2 = map(int, best_box)
    cropped = image.crop((x1, y1, x2, y2))

    all_boxes = boxes.xyxy.cpu().numpy().tolist()
    return cropped, all_boxes
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_yolo.py -v
```

Expected: PASS（注意：YOLO首次运行会下载模型权重，约6MB，需等待）

- [ ] **Step 5: Commit**

```bash
git add app/services/yolo.py tests/test_yolo.py
git commit -m "feat: add YOLO detection and crop module"
```

---

### Task 5: DINOv2特征提取模块

**Files:**
- Create: `app/services/dinov2.py`
- Create: `tests/test_dinov2.py`

- [ ] **Step 1: 编写 test_dinov2.py**

```python
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
    # 同一张图片两次提取特征应高度一致
    cos_sim = np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))
    assert cos_sim > 0.99
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_dinov2.py -v
```

Expected: FAIL — `extract_features` 未定义

- [ ] **Step 3: 实现 app/services/dinov2.py**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_dinov2.py -v
```

Expected: PASS（注意：DINOv2首次运行会下载模型权重，约1.2GB，需等待）

- [ ] **Step 5: Commit**

```bash
git add app/services/dinov2.py tests/test_dinov2.py
git commit -m "feat: add DINOv2 feature extraction module"
```

---

### Task 6: 阿里百炼API模块

**Files:**
- Create: `app/services/bailian.py`
- Create: `tests/test_bailian.py`

- [ ] **Step 1: 编写 test_bailian.py**

由于百炼API需要真实密钥和网络访问，单元测试使用mock方式：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_bailian.py -v
```

Expected: FAIL — `classify_category` 未定义

- [ ] **Step 3: 实现 app/services/bailian.py**

```python
import io
import logging
import base64
import httpx
from PIL import Image
from openai import OpenAI
from app.config import BAILIAN_API_KEY, BAILIAN_BASE_URL, BAILIAN_MODEL_NAME, BAILIAN_TIMEOUT

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=BAILIAN_API_KEY,
            base_url=BAILIAN_BASE_URL,
            timeout=BAILIAN_TIMEOUT,
        )
    return _client


def _call_api(image: Image.Image) -> object:
    """调用百炼多模态API，返回原始响应对象。"""
    client = _get_client()
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    response = client.chat.completions.create(
        model=BAILIAN_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": "请判断这张图片中零件的类别，只返回类别名称，不要解释。"},
                ],
            }
        ],
    )
    return response


def classify_category(image: Image.Image) -> str | None:
    """调用百炼API判断零件类别。失败时返回None（触发降级）。"""
    try:
        response = _call_api(image)
        category = response.choices[0].message.content.strip()
        logger.info(f"百炼API类别判断: {category}")
        return category
    except Exception as e:
        logger.warning(f"百炼API调用失败，将降级为全库检索: {e}")
        return None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_bailian.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/bailian.py tests/test_bailian.py
git commit -m "feat: add Bailian API classification module"
```

---

### Task 7: FAISS向量库模块

**Files:**
- Create: `app/services/vector_store.py`
- Create: `tests/test_vector_store.py`

- [ ] **Step 1: 编写 test_vector_store.py**

```python
import numpy as np
from app.services.vector_store import VectorStore
from app.config import DINOV2_FEATURE_DIM, FAISS_NLIST, FAISS_NPROBE


def test_add_and_search():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    # 添加10条测试数据
    for i in range(10):
        vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
        category = "cat_a" if i < 5 else "cat_b"
        store.add(vector=vec, id=i + 1, category=category)

    # 用cat_a的一条数据检索，应优先返回cat_a的数据
    query = store._vectors[0]  # 取第一条cat_a向量作为查询
    ids, sims = store.search(query, category="cat_a", top_k=3)
    assert len(ids) > 0
    assert all(store._category_map.get("cat_a", set()).__contains__(id_) for id_ in ids)


def test_search_without_category_filter():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    for i in range(10):
        vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
        store.add(vector=vec, id=i + 1, category="cat_a" if i < 5 else "cat_b")

    query = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    ids, sims = store.search(query, category=None, top_k=5)
    assert len(ids) > 0


def test_immediate_search_after_add():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    store.add(vector=vec, id=1, category="test_cat")
    # 添加后立即检索，验证实时性
    ids, sims = store.search(vec, category="test_cat", top_k=1)
    assert 1 in ids


def test_category_map_unknown_category():
    store = VectorStore(dim=DINOV2_FEATURE_DIM, nlist=FAISS_NLIST, nprobe=FAISS_NPROBE)
    query = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    # 未知类别降级为全库检索
    ids, sims = store.search(query, category="unknown_cat", top_k=3)
    # 空底库时应返回空结果
    assert len(ids) == 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_vector_store.py -v
```

Expected: FAIL — `VectorStore` 未定义

- [ ] **Step 3: 实现 app/services/vector_store.py**

```python
import logging
import numpy as np
import faiss
from app.config import DINOV2_FEATURE_DIM, FAISS_NLIST, FAISS_NPROBE, FAISS_INDEX_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS向量库管理：索引构建、动态添加、类别预过滤检索。"""

    def __init__(self, dim: int = DINOV2_FEATURE_DIM, nlist: int = FAISS_NLIST, nprobe: int = FAISS_NPROBE):
        self.dim = dim
        self.nlist = nlist
        self.nprobe = nprobe
        self._next_id = 1
        self._vectors: dict[int, np.ndarray] = {}
        self._category_map: dict[str, set[int]] = {}
        self._index: faiss.IndexIVFFlat | None = None
        self._index_trained = False

    def _ensure_index(self):
        """确保索引已创建并训练。初始阶段数据量少时使用Flat索引，数据量>nlist时切换到IVF。"""
        total = len(self._vectors)
        if self._index is None:
            if total < self.nlist:
                # 数据量不足nlist时用Flat索引
                self._index = faiss.IndexFlatL2(self.dim)
                self._index_trained = True
                logger.info(f"使用Flat索引（数据量{total} < nlist={self.nlist}）")
            else:
                quantizer = faiss.IndexFlatL2(self.dim)
                self._index = faiss.IndexIVFFlat(quantizer, self.dim, self.nlist)
                all_vecs = np.stack(list(self._vectors.values()))
                self._index.train(all_vecs)
                self._index.nprobe = self.nprobe
                self._index_trained = True
                # 重新添加所有已有向量
                for id_, vec in self._vectors.items():
                    self._index.add_with_ids(vec.reshape(1, -1), np.array([id_], dtype=np.int64))
                logger.info(f"使用IVF索引，训练完成（数据量{total} >= nlist={self.nlist}）")

    def add(self, vector: np.ndarray, id: int, category: str):
        """动态添加向量到索引，同时更新类别映射表。"""
        vector = vector.astype(np.float32).reshape(1, -1)
        self._vectors[id] = vector.squeeze()
        if category not in self._category_map:
            self._category_map[category] = set()
        self._category_map[category].add(id)

        self._ensure_index()
        self._index.add_with_ids(vector, np.array([id], dtype=np.int64))
        logger.info(f"向量添加成功: id={id}, category={category}")

    def search(self, query: np.ndarray, category: str | None = None, top_k: int = 10) -> tuple[list[int], list[float]]:
        """检索相似向量。category不为None时按类别预过滤，为None时全库检索（降级模式）。"""
        if self._index is None or len(self._vectors) == 0:
            return [], []

        self._ensure_index()
        query = query.astype(np.float32).reshape(1, -1)

        # 全库检索，取较多候选用于后续过滤
        search_k = top_k * 5 if category else top_k
        distances, ids = self._index.search(query, search_k)

        result_ids = []
        result_sims = []
        for dist, id_ in zip(distances[0], ids[0]):
            if id_ == -1:
                continue
            if category is not None:
                if id_ not in self._category_map.get(category, set()):
                    continue
            result_ids.append(int(id_))
            result_sims.append(float(dist))
            if len(result_ids) >= top_k:
                break

        return result_ids, result_sims

    def get_total_count(self) -> int:
        return len(self._vectors)

    def get_categories(self) -> list[str]:
        return list(self._category_map.keys())

    def save(self):
        """保存FAISS索引到磁盘。"""
        if self._index is not None:
            faiss.write_index(self._index, str(FAISS_INDEX_PATH))
            logger.info(f"FAISS索引已保存: {FAISS_INDEX_PATH}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_vector_store.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/vector_store.py tests/test_vector_store.py
git commit -m "feat: add FAISS vector store module with category filtering"
```

---

### Task 8: SQLite元数据存储模块

**Files:**
- Create: `app/services/metadata_store.py`
- Create: `tests/test_metadata_store.py`

- [ ] **Step 1: 编写 test_metadata_store.py**

```python
from app.services.metadata_store import MetadataStore
from app.config import DB_PATH


def test_add_and_get():
    store = MetadataStore(db_path=str(DB_PATH))
    store.add(id=1, category="螺栓", specification="M10x30", description="六角头螺栓", image_path="/uploads/bolt1.png")
    record = store.get(1)
    assert record is not None
    assert record["category"] == "螺栓"
    assert record["specification"] == "M10x30"
    assert record["description"] == "六角头螺栓"


def test_get_multiple():
    store = MetadataStore(db_path=str(DB_PATH))
    store.add(id=2, category="齿轮", specification="Z20", description="直齿轮", image_path="/uploads/gear1.png")
    store.add(id=3, category="齿轮", specification="Z30", description="斜齿轮", image_path="/uploads/gear2.png")
    records = store.get_batch([2, 3])
    assert len(records) == 2
    assert all(r["category"] == "齿轮" for r in records)


def test_get_nonexistent():
    store = MetadataStore(db_path=str(DB_PATH))
    result = store.get(999)
    assert result is None


def test_count():
    store = MetadataStore(db_path=str(DB_PATH))
    count = store.count()
    assert isinstance(count, int)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_metadata_store.py -v
```

Expected: FAIL — `MetadataStore` 未定义

- [ ] **Step 3: 实现 app/services/metadata_store.py**

```python
import sqlite3
import logging
from app.config import DB_PATH

logger = logging.getLogger(__name__)


class MetadataStore:
    """SQLite元数据存储：图文信息关联。"""

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                specification TEXT NOT NULL,
                description TEXT,
                image_path TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def add(self, id: int, category: str, specification: str, description: str | None, image_path: str, status: str = "active"):
        self._conn.execute(
            "INSERT INTO metadata (id, category, specification, description, image_path, status) VALUES (?, ?, ?, ?, ?, ?)",
            (id, category, specification, description, image_path, status),
        )
        self._conn.commit()
        logger.info(f"元数据写入成功: id={id}, category={category}")

    def get(self, id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM metadata WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_batch(self, ids: list[int]) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM metadata WHERE id IN ({})".format(",".join(map(str, ids)))
        ).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM metadata").fetchone()
        return row[0]

    def close(self):
        self._conn.close()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_metadata_store.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/metadata_store.py tests/test_metadata_store.py
git commit -m "feat: add SQLite metadata store module"
```

---

### Task 9: 学习端+使用端管道编排

**Files:**
- Create: `app/services/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: 编写 test_pipeline.py**

```python
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
from app.services.pipeline import learn_pipeline, search_pipeline
from app.config import DINOV2_FEATURE_DIM


def test_learn_pipeline_success():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
    mock_crop = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))

    with patch("app.services.pipeline.enhance_image", return_value=img) as mock_enhance, \
         patch("app.services.pipeline.yolo_detect_and_crop", return_value=(mock_crop, [])) as mock_yolo, \
         patch("app.services.pipeline.extract_features", return_value=np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)) as mock_dinov2, \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.metadata_store") as mock_ms:

        result = learn_pipeline(image=img, category="螺栓", specification="M10x30", description="六角头螺栓", image_path="/uploads/bolt1.png")
        assert result["status"] == "success"
        assert result["id"] > 0
        mock_vs.add.assert_called_once()
        mock_ms.add.assert_called_once()


def test_learn_pipeline_yolo_no_detection():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))

    with patch("app.services.pipeline.enhance_image", return_value=img), \
         patch("app.services.pipeline.yolo_detect_and_crop", return_value=None):

        result = learn_pipeline(image=img, category="螺栓", specification="M10x30", description="", image_path="/uploads/bolt1.png")
        assert result["status"] == "pending_review"


def test_search_pipeline_success():
    img = Image.fromarray(np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8))
    mock_crop = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)
    mock_search_result = ([1, 2, 3], [0.1, 0.2, 0.3])

    with patch("app.services.pipeline.yolo_detect_and_crop", return_value=(mock_crop, [])), \
         patch("app.services.pipeline.classify_category", return_value="螺栓"), \
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
    mock_crop = Image.fromarray(np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8))
    mock_vec = np.random.randn(DINOV2_FEATURE_DIM).astype(np.float32)

    with patch("app.services.pipeline.yolo_detect_and_crop", return_value=(mock_crop, [])), \
         patch("app.services.pipeline.classify_category", return_value=None), \
         patch("app.services.pipeline.extract_features", return_value=mock_vec), \
         patch("app.services.pipeline.vector_store") as mock_vs, \
         patch("app.services.pipeline.metadata_store") as mock_ms:

        mock_vs.search.return_value = ([1], [0.5])
        mock_ms.get_batch.return_value = [{"id": 1, "category": "螺栓", "specification": "M10", "description": "", "image_path": "/u/b1.png"}]

        result = search_pipeline(image=img, top_k=10)
        assert result["degraded"] is True
        assert result["query_category"] is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_pipeline.py -v
```

Expected: FAIL — `learn_pipeline` / `search_pipeline` 未定义

- [ ] **Step 3: 实现 app/services/pipeline.py**

```python
import logging
import time
from PIL import Image
import numpy as np
from app.services.enhance import enhance_image
from app.services.yolo import yolo_detect_and_crop
from app.services.dinov2 import extract_features
from app.services.bailian import classify_category
from app.services.vector_store import VectorStore
from app.services.metadata_store import MetadataStore
from app.config import FAISS_DEFAULT_TOP_K

logger = logging.getLogger(__name__)

vector_store = VectorStore()
metadata_store = MetadataStore()


def learn_pipeline(image: Image.Image, category: str, specification: str, description: str | None, image_path: str) -> dict:
    """学习端管道：图像增强→YOLO→DINOv2→FAISS+元数据写入。"""
    # Step 1: 图像增强
    enhanced = enhance_image(image)

    # Step 2: YOLO目标检测+裁剪
    crop_result = yolo_detect_and_crop(enhanced)
    if crop_result is None:
        logger.warning("YOLO未检测到目标，标记为待人工审核")
        return {"status": "pending_review", "message": "未检测到目标区域，需人工审核", "id": 0}

    cropped_image, boxes = crop_result

    # Step 3: DINOv2特征提取
    features = extract_features(cropped_image)

    # Step 4: 生成ID并写入FAISS+元数据
    new_id = int(time.time() * 1000) % (10 ** 9)  # 时间戳生成唯一ID
    vector_store.add(vector=features, id=new_id, category=category)
    metadata_store.add(id=new_id, category=category, specification=specification, description=description, image_path=image_path)

    logger.info(f"学习端入库成功: id={new_id}, category={category}")
    return {"status": "success", "id": new_id, "category": category, "specification": specification, "description": description, "message": "入库成功"}


def search_pipeline(image: Image.Image, top_k: int = FAISS_DEFAULT_TOP_K) -> dict:
    """使用端管道：YOLO→百炼API(类别预过滤)→DINOv2→FAISS检索→元数据取回。"""
    # Step 1: YOLO目标裁剪
    crop_result = yolo_detect_and_crop(image)
    if crop_result is None:
        return {"results": [], "query_category": None, "degraded": False, "message": "未检测到目标区域"}

    cropped_image, boxes = crop_result

    # Step 2: 百炼API类别判断（可为None，触发降级）
    category = classify_category(cropped_image)
    degraded = category is None

    # Step 3: DINOv2特征提取
    features = extract_features(cropped_image)

    # Step 4: FAISS检索（有类别则预过滤，无类别则全库检索）
    search_category = category if not degraded else None
    ids, similarities = vector_store.search(query=features, category=search_category, top_k=top_k)

    if len(ids) == 0:
        return {"results": [], "query_category": category, "degraded": degraded, "message": "未找到匹配项"}

    # Step 5: 从元数据存储取回完整图文信息
    records = metadata_store.get_batch(ids)
    results = []
    for record, sim in zip(records, similarities):
        results.append({
            "id": record["id"],
            "category": record["category"],
            "specification": record["specification"],
            "description": record["description"],
            "similarity": sim,
            "image_url": record["image_path"],
        })

    return {
        "results": results,
        "query_category": category,
        "degraded": degraded,
        "message": f"检索完成，返回{len(results)}条结果" + ("（降级模式：全库检索）" if degraded else ""),
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_pipeline.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline.py tests/test_pipeline.py
git commit -m "feat: add learn and search pipeline orchestration"
```

---

### Task 10: FastAPI路由实现

**Files:**
- Create: `app/routers/health.py`
- Create: `app/routers/learn.py`
- Create: `app/routers/search.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: 创建 app/routers/health.py**

```python
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.services.pipeline import vector_store, metadata_store

router = APIRouter()


@router.get("", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        db_count=metadata_store.count(),
        faiss_count=vector_store.get_total_count(),
        categories=vector_store.get_categories(),
    )
```

- [ ] **Step 2: 创建 app/routers/learn.py**

```python
from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image
import io
from app.models.schemas import LearnResponse
from app.services.pipeline import learn_pipeline
from app.config import UPLOAD_DIR

router = APIRouter()


@router.post("/upload", response_model=LearnResponse)
async def upload_item(
    image: UploadFile = File(..., description="零件图片"),
    category: str = Form(..., description="零件类别"),
    specification: str = Form(..., description="零件规格"),
    description: str = Form(None, description="零件描述"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    # 保存上传图片到data/uploads/
    image_path = str(UPLOAD_DIR / image.filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    result = learn_pipeline(
        image=pil_image,
        category=category,
        specification=specification,
        description=description,
        image_path=image_path,
    )
    return LearnResponse(
        id=result.get("id", 0),
        category=category,
        specification=specification,
        description=description,
        status=result["status"],
        message=result["message"],
    )
```

- [ ] **Step 3: 创建 app/routers/search.py**

```python
from fastapi import APIRouter, UploadFile, File, Form
from PIL import Image
import io
from app.models.schemas import SearchResponse, SearchResult
from app.services.pipeline import search_pipeline

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_item(
    image: UploadFile = File(..., description="待检索图片"),
    top_k: int = Form(default=10, description="返回TopK结果数量"),
):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    result = search_pipeline(image=pil_image, top_k=top_k)

    search_results = [
        SearchResult(
            id=r["id"],
            category=r["category"],
            specification=r["specification"],
            description=r["description"],
            similarity=r["similarity"],
            image_url=r["image_url"],
        )
        for r in result["results"]
    ]

    return SearchResponse(
        results=search_results,
        query_category=result.get("query_category"),
        degraded=result.get("degraded", False),
        message=result["message"],
    )
```

- [ ] **Step 4: 编写 tests/test_api.py**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["db_count"], int)
    assert isinstance(data["faiss_count"], int)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/test_api.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/routers/health.py app/routers/learn.py app/routers/search.py tests/test_api.py
git commit -m "feat: add FastAPI routes for learn, search, and health"
```

---

### Task 11: 端到端集成测试

**Files:**
- Modify: `tests/test_api.py`

- [ ] **Step 1: 创建合成测试图片**

```python
# 在tests目录下创建一个辅助函数生成测试图片
import io
from PIL import Image
import numpy as np


def create_test_image(size=(640, 640)):
    arr = np.random.randint(50, 200, (*size, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def image_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

- [ ] **Step 2: 在 test_api.py 中添加端到端测试**

追加以下测试到 `tests/test_api.py`：

```python
import io
import numpy as np
from PIL import Image


def _make_test_image_bytes():
    arr = np.random.randint(50, 200, (640, 640, 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_learn_and_search_flow():
    # 学习端上传
    img_buf = _make_test_image_bytes()
    learn_response = client.post(
        "/api/learn/upload",
        files={"image": ("test.png", img_buf, "image/png")},
        data={"category": "test_cat", "specification": "test_spec", "description": "test_desc"},
    )
    assert learn_response.status_code == 200
    learn_data = learn_response.json()
    # YOLO可能检测不到合成图，status可能是pending_review
    assert learn_data["status"] in ["success", "pending_review"]

    # 使用端检索
    img_buf2 = _make_test_image_bytes()
    search_response = client.post(
        "/api/search/query",
        files={"image": ("query.png", img_buf2, "image/png")},
        data={"top_k": "5"},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert isinstance(search_data["results"], list)
```

- [ ] **Step 3: 运行端到端测试**

```bash
python -m pytest tests/test_api.py -v
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "feat: add end-to-end integration test"
```

---

### Task 12: FAISS索引持久化与服务启动加载

**Files:**
- Modify: `app/services/vector_store.py`
- Modify: `app/main.py`

- [ ] **Step 1: 在 VectorStore 中添加 load 方法**

在 `app/services/vector_store.py` 的 `VectorStore` 类中添加 `load` 方法：

```python
    def load(self):
        """从磁盘加载FAISS索引。"""
        if FAISS_INDEX_PATH.exists():
            self._index = faiss.read_index(str(FAISS_INDEX_PATH))
            self._index_trained = True
            logger.info(f"FAISS索引已加载: {FAISS_INDEX_PATH}, 向量数={self._index.ntotal}")
        else:
            logger.info("FAISS索引文件不存在，将在首次添加时创建")
```

- [ ] **Step 2: 在 main.py 中添加启动事件，加载FAISS索引**

修改 `app/main.py`：

```python
from fastapi import FastAPI
from app.routers import learn, search, health
from app.services.pipeline import vector_store

app = FastAPI(title="工业仓库物流识别系统", version="1.0.0")


@app.on_event("startup")
def startup():
    vector_store.load()


@app.on_event("shutdown")
def shutdown():
    vector_store.save()

app.include_router(health.router)
app.include_router(learn.router, prefix="/api/learn", tags=["学习端"])
app.include_router(search.router, prefix="/api/search", tags=["使用端"])
```

- [ ] **Step 3: 运行全部测试确认无破坏**

```bash
python -m pytest tests/ -v
```

Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/services/vector_store.py app/main.py
git commit -m "feat: add FAISS index persistence and startup/shutdown hooks"
```

---

## Self-Review

**1. Spec coverage:**
- 学习端管道（图像增强→YOLO→DINOv2→FAISS+元数据）：Task 3-8实现各模块，Task 9编排管道，Task 10暴露API ✅
- 使用端管道（YOLO→百炼API→FAISS预过滤→DINOv2→检索）：Task 4,6,5,7,9,10覆盖 ✅
- FAISS类别预过滤：Task 7实现 ✅
- FAISS动态添加（实时生效）：Task 7实现 ✅
- 降级策略（百炼API不可用时全库检索）：Task 6返回None + Task 9降级逻辑 ✅
- 异常处理（YOLO未检测到目标）：Task 4返回None + Task 9处理 ✅
- 元数据存储（SQLite解耦）：Task 8实现 ✅
- 端到端集成测试：Task 11 ✅
- FAISS索引持久化：Task 12 ✅
- 客户端自助上传：Task 10 learn路由 ✅

**2. Placeholder scan:** 无TBD/TODO/模糊描述，所有步骤包含完整代码 ✅

**3. Type consistency:** dinov2_vitl14输出dim=1024，VectorStore初始化使用DINOV2_FEATURE_DIM=1024，各模块接口一致 ✅