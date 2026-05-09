# MLLN - 工业仓库物流识别系统

基于 DINOv2 + FAISS + 百炼 API 的工业零件智能识别系统。支持零件图片学习入库和相似度检索。

## 项目结构

```
planforme/
├── backend/              # FastAPI 后端
│   ├── app/              # 应用代码
│   │   ├── main.py       # 入口（CORS、路由、lifespan）
│   │   ├── config.py     # 配置（路径、模型参数）
│   │   ├── routers/      # API 路由（learn/search/warehouse/health）
│   │   ├── services/     # 核心服务（DINOv2、FAISS、百炼、元数据）
│   │   └── models/       # Pydantic 模型
│   ├── data/             # 运行时数据（SQLite、FAISS索引、上传图片）
│   ├── rebuild_faiss.py  # FAISS 索引重建脚本
│   ├── requirements.txt
│   ├── run.py            # 本地启动入口
│   └── Dockerfile
├── frontend/             # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue       # 主布局（导航栏、扫描动画）
│   │   ├── views/        # 页面（LearnView/SearchView/WarehouseView）
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── router/       # Vue Router（history 模式）
│   │   ├── api/          # Axios 客户端
│   │   └── assets/       # CSS（工业精度仪表盘风格）
│   ├── vite.config.js    # 开发代理配置
│   ├── Dockerfile
│   └── package.json
├── nginx.conf            # Nginx 配置（SPA + API 反向代理）
├── docker-compose.yml
└── README.md
```

## 快速开始

### 方式一：本地开发

**1. 启动后端**

```bash
cd backend
cp .env.example .env          # 复制配置文件，填入百炼 API 密钥
pip install -r requirements.txt
python run.py                 # 启动 uvicorn，端口 8000
```

首次启动会自动下载 DINOv2 模型（约 1.5GB），需要等待几分钟。

**2. 启动前端**

```bash
cd frontend
npm install
npm run dev                   # 启动 Vite 开发服务器，端口 3000
```

Vite 会自动将 `/api` 和 `/uploads` 请求代理到后端 `localhost:8000`。

打开浏览器访问 http://localhost:3000

### 方式二：Docker 部署

```bash
cp backend/.env.example backend/.env   # 填入百炼 API 密钥
docker-compose up --build
```

启动后访问 http://localhost（端口 80）。Nginx 负责前端静态文件和 API 反向代理。

## 功能说明

| 页面 | 路径 | 功能 |
|------|------|------|
| 学习端 | /learn | 上传零件图片，填写类别/规格，批量入库 |
| 使用端 | /search | 上传查询图片，FAISS 相似度检索 + 百炼类别判断 |
| 仓库 | /warehouse | 浏览底库所有记录，按类别筛选 |

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 系统状态（数据库计数、FAISS计数、类别列表） |
| `/api/learn/upload` | POST | 学习入库（multipart: image + category + specification） |
| `/api/search/query` | POST | 相似度检索（multipart: image + top_k） |
| `/api/warehouse/list` | GET | 仓库浏览（返回所有活跃记录） |

## 环境变量

在 `backend/.env` 中配置：

```
BAILIAN_API_KEY=你的阿里百炼API密钥
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL_NAME=qwen-vl-max-latest
BAILIAN_TIMEOUT=10.0
```

## FAISS 索引重建

如果索引损坏或需要从数据库重建：

```bash
cd backend
python rebuild_faiss.py
```

该脚本会从 metadata 数据库读取所有活跃记录，重新提取图片特征并批量构建 FAISS 索引。

## 技术栈

- **后端**: FastAPI + DINOv2 (vitl14, 1024维) + FAISS IndexIDMap(IndexFlatL2) + SQLite + 百炼 API (dashscope)
- **前端**: Vue 3 + Vite + Pinia + Vue Router 4 + Axios
- **部署**: Docker Compose (nginx + FastAPI)
- **风格**: 工业精度仪表盘（钨钢黑 + 钢蓝 + 金色点缀）