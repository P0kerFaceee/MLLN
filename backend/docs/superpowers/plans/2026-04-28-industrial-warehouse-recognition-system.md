# 工业仓库物流识别系统 — 项目当前状态

> 本文档记录项目的实际实现状态，与设计文档（specs）对应。

## 已完成里程碑

### MVP阶段 ✅

1. **后端核心管道** — 学习端（图像增强→DINOv2整图特征→FAISS写入）和使用端（百炼API参考→DINOv2→FAISS全库检索）完整链路贯通
2. **前端SPA** — Vue 3 + Vite 三页面（学习端/使用端/仓库浏览），工业精度仪表盘风格
3. **Docker部署** — Docker Compose（nginx前端 + FastAPI后端）
4. **24张测试照片**覆盖6个类别验证功能可用

### 关键架构变更（与初始设计对比）

| 初始设计 | 实际实现 | 原因 |
|----------|----------|------|
| YOLO目标检测+裁剪 | 移除YOLO，整图特征提取 | 工业零件图片背景单一，裁剪反而引入不稳定因素；YOLO通用模型对小零件检测率低 |
| 百炼API类别预过滤FAISS | 百炼API仅作参考，FAISS全库检索 | DINOv2特征本身具备相似度匹配能力；类别预过滤在类别判断不准确时反而降低召回 |
| IndexIVFFlat+类别分区 | IndexIDMap(IndexFlatL2/IVFFlat) | IndexIDMap确保ID-向量稳定映射；小数据量用Flat更精确；动态add_with_ids无需重建 |
| Vue 2 CDN SPA | Vue 3 + Vite SFC SPA | 前后端分离便于nginx部署；Composition API + Pinia更易维护 |
| /health 无前缀 | /api/health | 统一API路径前缀，便于nginx反向代理 |
| 无仓库浏览 | /api/warehouse/list + WarehouseView | 客户需要查看底库内容和按类别筛选 |
| 相似度固定公式 | 相似度相对缩放(最佳=100%,最差=0%) | 固定maxDist在不同数据分布下失效 |
| Python 3.14 | Python 3.11 | torch/faiss兼容性考虑 |

### 修复的关键Bug

| Bug | 根因 | 修复 |
|-----|------|------|
| 搜索返回错误ID，L2=0.0 | FAISS load()在_vectors字典中填充np.zeros占位符，重建索引时使用零向量 | load()不再填充占位符，类别映射从metadata DB重建 |
| 进程被杀后索引丢失 | lifespan shutdown的save()未执行 | 每次add后自动save() |
| top_k=-1导致500错误 | 无参数校验 | 添加ge=1, le=50 Form验证 |
| DB计数与FAISS计数不一致 | metadata count()不过滤deleted记录 | health接口暴露两个计数供监控 |

## 当前文件结构

```
planforme/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI入口，CORS，lifespan（load+类别重建）
│   │   ├── config.py           # 路径配置，模型参数，.env加载
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py      # Pydantic模型（Learn/Search/Warehouse/Health）
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── health.py       # GET /api/health
│   │   │   ├── learn.py        # POST /api/learn/upload
│   │   │   ├── search.py       # POST /api/search/query
│   │   │   └── warehouse.py   # GET /api/warehouse/list
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── enhance.py      # 图像增强（中值滤波+对比度+亮度）
│   │       ├── dinov2.py       # DINOv2特征提取（dinov2_vitl14, dim=1024）
│   │       ├── bailian.py      # 百炼API类别判断（OpenAI兼容接口）
│   │       ├── vector_store.py # FAISS向量库（IndexIDMap+类别映射+save/load/重建）
│   │       ├── metadata_store.py # SQLite元数据存储
│   │       └── pipeline.py     # 学习端+使用端管道编排（单例vector_store/metadata_store）
│   │       └── yolo.py         # 保留但未使用（已从管道移除）
│   ├── data/                   # 运行时数据（不入git）
│   │   ├── db/metadata.db
│   │   ├── faiss/index.faiss
│   │   └── uploads/            # 上传图片
│   ├── rebuild_faiss.py        # 批量重建索引（带L2=0验证）
│   ├── requirements.txt
│   ├── run.py                  # uvicorn启动（reload_dirs=["app"]）
│   ├── Dockerfile              # Python 3.11-slim
│   ├── .env                    # API密钥
│   ├── .env.example
│   └── tests/                  # 单元测试
│   └── docs/                   # 设计文档
├── frontend/
│   ├── src/
│   │   ├── App.vue             # 主布局（扫描动画+导航+系统状态）
│   │   ├── main.js             # createApp + Pinia + Router
│   │   ├── api/index.js        # Axios实例（baseURL=/api）
│   │   ├── stores/system.js    # Pinia（dbCount, categories, isScanning, fetchHealth）
│   │   ├── router/index.js     # Vue Router 4 history模式（/learn /search /warehouse）
│   │   ├── views/
│   │   │   ├── LearnView.vue   # 学习端（批量上传+元数据表单+底库状态）
│   │   │   ├── SearchView.vue  # 使用端（查询上传+相对相似度+降级标识）
│   │   │   └── WarehouseView.vue # 仓库浏览（类别筛选+刷新）
│   │   └── assets/styles/
│   │       ├── variables.css   # 设计Token（CSS自定义属性）
│   │       └── main.css        # 全局样式（工业精度仪表盘）
│   ├── index.html              # SPA入口
│   ├── vite.config.js          # 开发代理（/api→localhost:8000）
│   ├── package.json            # Vue 3, Vite, Pinia, Vue Router 4, Axios
│   └── Dockerfile              # Node 20构建 → nginx
├── nginx.conf                  # SPA history + /api + /uploads 反向代理
├── docker-compose.yml          # backend + frontend 服务
└── README.md                   # 运行说明
```

## 优化阶段（下一步）

根据实际数据反馈，以下方面可优化：

1. **百炼API类别参考增强** — 当前仅展示类别名称，可加入置信度展示、人工修正类别写入底库
2. **FAISS IVF切换** — 数据量超过100时自动从FlatL2切换到IVFFlat
3. **YOLO微调**（可选） — 如客户需要混合场景（多个零件在一张图中），可重新引入微调后的YOLO
4. **数据库升级** — 如需支持多用户/事务场景，可从SQLite迁移到PostgreSQL
5. **metadata_store.count() 修复** — 应过滤 deleted 状态记录，使 db_count 与 faiss_count 一致