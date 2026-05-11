# MLLN - 工业仓库物流识别系统

基于 DINOv2 + FAISS + 百炼 API 的工业零件智能识别系统。支持零件级管理（多角度照片归组）、规格 key-value 录入、仓库 CRUD、零件级相似度检索（Best-of-Part + 扎堆加分）。

## 项目结构

```
planforme/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 入口（CORS、路由、lifespan、自动迁移）
│   │   ├── config.py     # 配置（路径、模型参数、FAISS参数）
│   │   ├── routers/      # API 路由（warehouse/search/specs/health）
│   │   ├── services/     # 核心服务
│   │   │   ├── part_store.py    # 三表管理（parts/photos/spec_keys/stats_meta）
│   │   │   ├── pipeline.py      # 入库管道 + 零件级搜索管道
│   │   │   ├── vector_store.py  # FAISS 向量库（IndexIDMap + category预过滤）
│   │   │   ├── dinov2.py        # DINOv2 特征提取
│   │   │   ├── enhance.py       # 图片增强
│   │   │   ├── bailian.py       # 百炼类别判断
│   │   │   └── migration.py     # metadata→parts+photos 数据迁移
│   │   └── models/       # Pydantic 模型（PartItem/SearchResult等）
│   ├── data/             # 运行时数据（SQLite、FAISS索引、上传图片）
│   ├── rebuild_faiss.py  # FAISS 索引重建 + 统计量计算
│   ├── requirements.txt
│   ├── run.py            # 本地启动入口
│   └── Dockerfile
├── frontend/             # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue       # 主布局（两tab导航：使用端+仓库）
│   │   ├── views/
│   │   │   ├── SearchView.vue    # 零件级搜索 + 百分比相似度 + 高优先级标记
│   │   │   └── WarehouseView.vue # 零件CRUD + 新增零件模态框 + 照片管理
│   │   ├── stores/       # Pinia（system + warehouse）
│   │   ├── router/       # Vue Router（/search + /warehouse）
│   │   ├── api/          # Axios 客户端
│   │   └── assets/       # CSS（工业精度仪表盘风格）
│   ├── vite.config.js
│   ├── Dockerfile
│   └── package.json
├── nginx.conf
├── docker-compose.yml
└── README.md
```

## 快速开始

### 本地开发

**1. 启动后端**

```bash
cd backend
cp .env.example .env          # 填入百炼 API 密钥
pip install -r requirements.txt
python run.py                 # uvicorn 端口 8000
```

首次启动自动下载 DINOv2 模型（~1.5GB）。如果存在旧 metadata 表，自动迁移到 parts+photos 表。

**2. 启动前端**

```bash
cd frontend
npm install
npm run dev                   # Vite 端口 3000，自动代理 /api 和 /uploads 到后端
```

浏览器打开 http://localhost:3000

### Docker 部署

```bash
cp backend/.env.example backend/.env
docker-compose up --build
```

访问 http://localhost（端口 80）。Nginx 负责前端静态文件和 API 反向代理。

### FAISS 索引重建

```bash
cd backend
python rebuild_faiss.py       # 从 parts+photos 表重建索引 + 计算距离统计量
```

## 数据模型

**parts（零件主表）** — 同类别下名称唯一

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 毫秒时间戳 mod 10^9 |
| name | TEXT | 零件名称（如"夹线器压线螺丝"） |
| category | TEXT | 类别（如"夹线器"） |
| specs | TEXT (JSON) | 规格 key-value（如 {"长度":"30mm","材质":"不锈钢"}） |
| description | TEXT | 简介/备注 |
| status | TEXT | active / deleted |

**photos（照片表）** — 每张照片对应一个 FAISS 向量

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 同时作为 FAISS 向量 ID |
| part_id | INTEGER FK | 所属零件 |
| image_path | TEXT | `/uploads/<filename>` |
| angle | TEXT | 角度标签（如"正面"、"侧1"） |

**spec_keys（规格 key 字典）** — 辅助规格录入的预定义 key 下拉

**stats_meta（距离统计量）** — 存储 L2 距离的 dist_mean 和 dist_std，用于百分比化映射

## 搜索策略

1. 图片增强 → 百炼判断类别 → 类别预过滤
2. DINOv2 提取特征 → FAISS 搜索 top_k×5 张照片
3. **零件级聚合**：照片结果按 part_id 分组
4. **Best-of-Part + 扎堆加分**：每零件取最小 L2 的百分比，次近照片给予 capped 5% boost
5. **硬规则**：>85% 相似度零件前置高优先级
6. **L2 百分比化**：`similarity% = max(0, min(100, (1 - (L2 - μ) / (3σ)) × 100))`

## 页面说明

| 页面 | 路径 | 功能 |
|------|------|------|
| 使用端 | /search | 上传查询图片 → 返回最相似零件列表（百分比相似度 + 高优先级标记） |
| 仓库 | /warehouse | 零件列表+CRUD（新增/删除零件、添加/删除照片、编辑规格） |

## API 接口

### 仓库 CRUD

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/warehouse/parts` | GET | 零件列表（category/name 筛选） |
| `/api/warehouse/parts/{id}` | GET | 零件详情+所有照片 |
| `/api/warehouse/parts` | POST | 新增零件（FormData: name, category, specs, images[], angles[]） |
| `/api/warehouse/parts/{id}` | PUT | 修改零件信息 |
| `/api/warehouse/parts/{id}` | DELETE | 删除零件+FAISS向量 |
| `/api/warehouse/parts/{id}/photos` | POST | 添加照片 |
| `/api/warehouse/parts/{id}/photos/{photo_id}` | DELETE | 删除照片+FAISS向量 |

### 搜索

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/search/query` | POST | 零件级检索（multipart: image + top_k） |

### 其他

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 系统状态 |
| `/api/specs/keys` | GET/POST/DELETE | 规格 key 字典管理 |

## 环境变量

`backend/.env` 配置：

```
BAILIAN_API_KEY=你的阿里百炼API密钥
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL_NAME=qwen-vl-max-latest
BAILIAN_TIMEOUT=10.0
```

## 技术栈

- **后端**: FastAPI + DINOv2 (vitl14, 1024维) + FAISS IndexIDMap(IndexFlatL2) + SQLite + 百炼 API
- **前端**: Vue 3 (Composition API) + Vite + Pinia + Vue Router 4 + Axios
- **部署**: Docker Compose (nginx + FastAPI)
- **风格**: 工业精度仪表盘（钨钢黑 + 钢蓝 + 金色点缀）