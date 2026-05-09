# 工业仓库物流识别系统设计

## 1. 需求概要

| 项目 | 值 |
|------|-----|
| 零件类型 | 混合（标准件+非标件），需同时支持类别识别和规格匹配 |
| 底库规模 | >10k 条记录（当前测试数据 24 条，6个类别） |
| 部署环境 | 内网服务器集群（有API出口访问阿里百炼），Docker Compose 部署 |
| 多模态大模型 | 阿里百炼平台 API（dashscope） |
| 响应时间 | 实时 <5s |
| 底库时效性 | 学习端上传后使用端需立刻可检索 |
| DINOv2模型 | dinov2_vitl14，特征向量维度1024 |
| 前端 | Vue 3 + Vite SPA，工业精度仪表盘风格 |

## 2. 整体架构与数据流

### 学习端（底库构建管道）

```
原始图片 → 图像增强 → DINOv2(dinov2_vitl14)整图特征提取 → FAISS写入
                                                        ↓
                                                  关联元数据（类别、规格、描述等）
                                                        ↓
                                                  FAISS向量+元数据底库
```

**关键变更**：已移除 YOLO 目标检测/裁剪步骤，改用整图特征提取。工业零件图片通常目标明确、背景单一，整图特征比裁剪子图更稳定可靠。

### 使用端（检索管道）

```
输入图片 → 图像增强 → 百炼API类别判断(参考) → DINOv2整图特征提取 → FAISS全库检索 → TopX结果 → 元数据存储取回完整图文 → 返回
```

**关键变更**：百炼API类别判断仅作**参考展示**，不再用于 FAISS 类别预过滤。DINOv2 特征本身具备相似度匹配能力，全库检索在当前数据规模下性能充足。百炼API不可用时自动降级为全库检索。

### 预计延迟

- 图像增强：~0.05s
- 百炼API（阿里百炼国内网络）：~1-2s（参考，不影响检索流程）
- DINOv2特征提取：~0.3-0.5s
- FAISS全库检索：~0.1s
- **总计：~0.5-1s**，远超 <5s 目标

## 3. 核心模块职责与接口定义

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| 图像增强模块 | 去噪、对比度调整、光照校正预处理 | 原始图片(BLOB) | 增强后图片(BLOB) |
| 百炼API模块 | 调用阿里百炼多模态API，判断零件类别（参考用途） | 图片(BLOB) | 类别标签(string) 或 None(降级) |
| DINOv2特征模块 | 提取整图向量特征(dinov2_vitl14) | 图片(BLOB) | 特征向量(float[], dim=1024) |
| FAISS向量库模块 | 向量存储、全库相似度检索、动态添加 | 向量+ID 或 查询向量 | TopX结果列表(ID+距离) |
| 元数据存储模块 | 存储并关联类别、规格、描述、图片等完整信息 | 元数据对象 | 匹配结果的完整图文信息 |

模块间依赖关系：

```
学习端: 图像增强 → DINOv2 → FAISS写入
                     ↕
                元数据存储 ← 元数据输入

使用端: 图像增强 → 百炼API(参考) → DINOv2 → FAISS全库检索 → 元数据存储(取图文)
```

FAISS向量库和元数据存储解耦：FAISS只存向量+ID+类别标签，元数据存储（SQLite）存完整图文信息。检索时FAISS返回ID列表，再从元数据存储中取回完整信息。

## 4. FAISS索引策略与实时更新机制

### 索引选择

使用 **IndexIDMap(IndexFlatL2)**（小数据量）或 **IndexIDMap(IndexIVFFlat)**（大数据量）：

- IndexIDMap 包装确保向量与ID的稳定映射，支持动态 add_with_ids
- 数据量 < nlist(100) 时使用 FlatL2（精确检索）
- 数据量 >= nlist 时切换到 IVFFlat（聚类加速检索）
- 向量维度：1024（匹配 dinov2_vitl14 输出）

### 类别映射与重建

维护内存中 **类别→ID集合** 映射表，用于仓库浏览页面按类别筛选：

```
类别映射: {
    "夹线器": [id_1, id_5, ...],
    "压缩弹簧": [id_2, id_8, ...],
    ...
}
```

**关键修复**：服务器重启后 FAISS load() 只恢复索引结构，不填充占位零向量到 _vectors 字典（此前的占位零向量曾导致重建索引时使用零向量，引发 L2=0.0 匹配错误ID的严重bug）。类别映射从 metadata 数据库重建。

### 实时更新机制

学习端每上传一条新记录：

1. DINOv2提取特征 → IndexIDMap.add_with_ids(vector, new_id)
2. 自动保存索引到磁盘（每次add后立即save）
3. 元数据写入SQLite → 关联 new_id
4. 类别映射表更新 → category_map[category].add(new_id)
5. 全部操作完成后立即可检索

## 5. 异常处理与边界情况

### 使用端关键路径异常处理

| 异常场景 | 处理策略 |
|----------|----------|
| 百炼API调用超时/失败 | 降级：跳过类别参考，FAISS全库向量检索，前端显示降级标识 |
| 百炼API返回未知类别 | 正常返回检索结果，前端显示百炼判断类别供参考 |
| DINOv2特征提取失败 | 返回"特征提取异常"错误，不做FAISS检索 |
| FAISS检索无结果 | 返回"未找到匹配项"提示 |

### 学习端异常处理

| 异常场景 | 处理策略 |
|----------|----------|
| 图像增强失败 | 跳过增强步骤，使用原始图片继续后续流程 |
| 元数据字段缺失（类别/规格为空） | 前端表单校验阻止提交 |

**降级核心原则**：使用端优先保证"有结果返回"。百炼API是参考增强而非必选依赖，不可用时自动降级到全库检索。

### FAISS数据一致性

| 异常场景 | 处理策略 |
|----------|----------|
| FAISS索引文件丢失 | 启动时从metadata数据库重建（rebuild_faiss.py脚本） |
| 进程被杀导致索引未保存 | 每次add后自动save，并提供rebuild_faiss.py批量重建脚本 |
| 数据库计数与FAISS计数不一致 | health接口暴露db_count和faiss_count供监控 |
| 重复图片导致IndexIDMap只返回一个ID | metadata标记重复记录为deleted状态 |

## 6. 前端架构

### 技术选型

| 层面 | 技术 | 说明 |
|------|------|------|
| 框架 | Vue 3 + Vite | SFC单文件组件，Composition API（script setup） |
| 状态管理 | Pinia | 跨组件共享 dbCount、categories、isScanning |
| 路由 | Vue Router 4 | history模式，/learn /search /warehouse |
| HTTP客户端 | Axios | baseURL=/api，Vite开发代理转发到后端 |
| 设计风格 | 工业精度仪表盘 | 钨钢黑 + 钢蓝 + 金色点缀 |

### 页面功能

| 页面 | 路径 | 功能 |
|------|------|------|
| 学习端 | /learn | 批量图片上传 + 类别/规格元数据表单 + 上传结果反馈 + 底库状态 |
| 使用端 | /search | 查询图片上传 + Top-K设置 + 相似度结果（相对缩放：最佳=100%，最差=0%） + 百炼类别参考 + 降级标识 |
| 仓库 | /warehouse | 底库浏览 + 类别筛选 + 图片缩略图 + 规格描述 |

### 相似度展示策略

FAISS返回L2距离（越小越相似），前端使用相对缩放：

- 最佳匹配（最小L2）= 100%
- 最差匹配（最大L2）= 0%
- 中间值线性插值

这避免了固定maxDist公式在不同数据分布下失效的问题。

## 7. 部署架构

### Docker Compose 部署

| 服务 | 容器 | 说明 |
|------|------|------|
| backend | Python 3.11 + uvicorn | FastAPI服务，端口8000，数据卷持久化 |
| frontend | Node 20构建 → nginx | Vue 3 SPA静态文件 + API反向代理，端口80 |

### Nginx 配置

- `try_files $uri $uri/ /index.html` — SPA history模式路由
- `location /api/` → proxy_pass backend:8000 — API请求转发
- `location /uploads/` → proxy_pass backend:8000 — 图片文件转发

### 本地开发

后端 `cd backend && python run.py`（端口8000），前端 `cd frontend && npm run dev`（端口3000，Vite代理转发API请求）。

## 8. API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 系统状态（db_count, faiss_count, categories） |
| `/api/learn/upload` | POST | 学习入库（multipart: image + category + specification + description） |
| `/api/search/query` | POST | 相似度检索（multipart: image + top_k） |
| `/api/warehouse/list` | GET | 仓库浏览（返回所有活跃记录） |

## 9. 项目结构

```
planforme/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 入口（CORS、路由、lifespan、类别映射重建）
│   │   ├── config.py         # 配置（路径、模型参数、API密钥从.env加载）
│   │   ├── routers/
│   │   │   ├── health.py     # /api/health
│   │   │   ├── learn.py      # /api/learn/upload
│   │   │   ├── search.py     # /api/search/query
│   │   │   └── warehouse.py  # /api/warehouse/list
│   │   ├── services/
│   │   │   ├── enhance.py    # 图像增强
│   │   │   ├── dinov2.py     # DINOv2特征提取（整图）
│   │   │   ├── bailian.py    # 百炼API类别判断（参考）
│   │   │   ├── vector_store.py  # FAISS索引管理（IndexIDMap + 类别映射 + 重建）
│   │   │   ├── metadata_store.py  # SQLite元数据存储
│   │   │   └── pipeline.py   # 学习端+使用端管道编排
│   │   └── models/
│   │       └── schemas.py    # Pydantic数据模型
│   ├── data/                 # 运行时数据（SQLite + FAISS + uploads）
│   ├── rebuild_faiss.py      # 批量重建索引脚本
│   ├── requirements.txt
│   ├── run.py                # 本地启动入口
│   ├── Dockerfile
│   └── .env                  # API密钥配置
├── frontend/                 # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── App.vue           # 主布局（导航栏 + 扫描动画 + 系统状态）
│   │   ├── views/            # 页面组件（Composition API script setup）
│   │   ├── stores/           # Pinia状态管理
│   │   ├── router/           # Vue Router 4 history模式
│   │   ├── api/              # Axios客户端
│   │   └── assets/styles/    # CSS（工业精度仪表盘风格）
│   ├── vite.config.js        # 开发代理配置
│   ├── Dockerfile            # 多阶段构建（Node → nginx）
│   └── package.json
├── nginx.conf                # Nginx配置（SPA + API反向代理）
├── docker-compose.yml        # Docker Compose编排
└── README.md                 # 运行说明文档
```

## 10. 技术栈

| 层面 | 技术 | 版本/说明 |
|------|------|----------|
| 后端框架 | FastAPI | Python 3.11 |
| 特征提取 | DINOv2 vitl14 | torch, 1024维特征 |
| 向量检索 | FAISS | IndexIDMap(IndexFlatL2/IndexIVFFlat), faiss-cpu |
| 类别参考 | 阿里百炼API | dashscope, qwen-vl-max-latest |
| 元数据 | SQLite | metadata.db |
| 前端框架 | Vue 3 + Vite | Composition API, Pinia, Vue Router 4 |
| HTTP | Axios | baseURL=/api |
| 部署 | Docker Compose | nginx + FastAPI |