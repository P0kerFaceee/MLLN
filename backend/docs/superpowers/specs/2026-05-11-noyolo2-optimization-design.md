---
name: noyolo2-optimization
description: MLLN优化改进设计：零件分组、规格key-value、仓库CRUD、使用端零件级搜索+多视角融合+百分比化
type: spec
created: 2026-05-11
---

# MLLN 优化改进设计 (noyolo2 分支)

## 概述

当前系统以"照片"为最小单位——每张照片独立存储、独立搜索、独立展示。本优化引入"零件"概念，将同一零件的多角度照片归组，仓库端和搜索端以零件维度展示，并支持完整的CRUD操作。

核心变化：
- 数据模型从单表重构为三表（parts + photos + spec_keys）
- 去掉独立的学习端页面，仓库端整合新增零件功能
- 搜索返回零件而非照片，采用 Best-of-Part + 扎堆加分策略
- L2距离用统计分布映射百分比化（不再用相对百分比）
- 兜底硬规则：类别阈值保护 + 扎堆增益封顶

## §1 数据模型

### parts 表（零件主表）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PK | 毫秒时间戳 mod 10^9 |
| `name` | TEXT NOT NULL | 零件名称，如"夹线器压线螺丝"，用于显示和模糊搜索 |
| `category` | TEXT NOT NULL | 类别，如"夹线器"，用于分类筛选和百炼预过滤 |
| `specs` | TEXT (JSON) | 规格信息JSON，如 `{"长度":"30mm","材质":"不锈钢"}` |
| `description` | TEXT (nullable) | 简介/备注 |
| `status` | TEXT DEFAULT 'active' | active / deleted |
| `created_at` | TIMESTAMP | 创建时间 |

**约束：** `UNIQUE(category, name)` — 同类别下零件名称不能重复

### photos 表（照片表）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PK | 毫秒时间戳 mod 10^9，同时作为 FAISS 向量 ID |
| `part_id` | INTEGER FK → parts.id | 所属零件 |
| `image_path` | TEXT NOT NULL | `/uploads/<filename>` |
| `angle` | TEXT (nullable) | 角度标签，如"正"、"侧1"、"侧2" |
| `status` | TEXT DEFAULT 'active' | active / deleted |
| `created_at` | TIMESTAMP | 创建时间 |

### spec_keys 表（规格key字典配置）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `key_name` | TEXT NOT NULL UNIQUE | 如"长度"、"材质"、"直径" |
| `unit` | TEXT (nullable) | 建议单位，如"mm"、"kg" |

### FAISS 关联

FAISS向量ID = photo.id，不变。`category_map` 改为从 parts 表读取（通过 photo → part 关联查询）。

### 数据迁移

现有 24 条 metadata 记录迁移到 parts+photos 表：
- 相同 `category+specification` 组合归为一个 part
- `name` 取 specification 值
- `specs` 为空 JSON `{}`，`description` 迁移
- FAISS 索引 ID 不变（photo.id = 原 metadata.id）

## §2 页面结构

### 导航（两页）

| 页面 | 路由 | 说明 |
|---|---|---|
| 使用端 | `/search` | 搜索查询+结果展示 |
| 仓库 | `/warehouse` | 零件列表+CRUD+新增零件 |

**移除** `/learn` 路由和 LearnView.vue。导航栏从三个tab变为两个。

### 仓库端新增零件

仓库页面顶部「新增零件」按钮，点击弹出表单面板，包含：
- **类别**（下拉，从已有类别选择，或输入新类别）
- **零件名称**（必填，同类别下唯一）
- **规格信息**（key-value 动态输入，key 从 spec_keys 字典下拉选择，value 手动输入，可添加多组）
- **简介/备注**（可选）
- **照片上传**（拖拽/选择多张图片，每张可选标注角度如"正"、"侧1"）

提交后创建 part 记录 → 逐张照片处理（增强 → DINOv2 → FAISS写入）→ 创建 photo 记录。

### 给已有零件添加照片

零件详情面板内有「添加照片」按钮，上传新照片并可选标注角度。

## §3 API 设计

### 仓库端 CRUD

| 操作 | API | 方法 | 说明 |
|---|---|---|---|
| 零件列表 | `/api/warehouse/parts` | GET | 参数: `category`(可选), `name`(可选,模糊搜索)。返回零件列表含每零件3张缩略图+基本信息 |
| 零件详情 | `/api/warehouse/parts/{id}` | GET | 返回零件全部信息+所有照片+规格 |
| 新增零件 | `/api/warehouse/parts` | POST | FormData: name, category, specs(JSON), description, images[], angles[] |
| 删除零件 | `/api/warehouse/parts/{id}` | DELETE | 标记 part+所有 photos 为 deleted，从 FAISS 移除对应向量 |
| 修改信息 | `/api/warehouse/parts/{id}` | PUT | 修改 name/category/specs/description |
| 添加照片 | `/api/warehouse/parts/{id}/photos` | POST | FormData: image, angle(可选) |
| 删除照片 | `/api/warehouse/parts/{id}/photos/{photo_id}` | DELETE | 标记 photo 为 deleted，从 FAISS 移除向量 |

### 规格 key 字典管理

| 操作 | API | 方法 | 说明 |
|---|---|---|---|
| 获取key列表 | `/api/specs/keys` | GET | 返回所有可用的 spec_key |
| 添加新key | `/api/specs/keys` | POST | 参数: key_name, unit |
| 删除key | `/api/specs/keys/{id}` | DELETE | 删除某个 spec_key（仅当未被任何零件使用时允许） |

### 搜索端（不变路由，变返回结构）

`POST /api/search/query` — 接收参数不变（image, top_k），返回结构改为零件维度：

```json
{
  "results": [
    {
      "part_id": 329468591,
      "name": "夹线器压线螺丝",
      "category": "夹线器",
      "specs": {"长度": "30mm", "材质": "不锈钢"},
      "description": "...",
      "best_similarity": 78.3,
      "best_photo_url": "/uploads/xxx.jpg",
      "best_photo_angle": "侧1",
      "thumbnail_urls": ["...正.jpg", "...侧1.jpg", "...侧2.jpg"],
      "total_photos": 4
    }
  ],
  "query_category": "夹线器",
  "degraded": false,
  "message": "..."
}
```

`best_similarity` 为百分比化后的值（0-100），不是原始L2距离。

## §4 搜索策略

### 管道流程

1. 增强图片 → 百炼判断类别 → 类别预过滤（不变）
2. DINOv2提取特征 → FAISS搜索 top_k×5 张照片（不变）
3. **零件级聚合**：将照片搜索结果按 part_id 分组
4. 每零件计算相似度：**Best-of-Part + 扎堆加分**
5. 兜底硬规则检查
6. 返回 top_k 个零件（按相似度排序）

### Best-of-Part + 扎堆加分

- **零件相似度** = 该零件所有照片中与查询图片 L2 距离最小（最相似）的那张的百分比化相似度
- **扎堆加分**：同一零件有多张照片进入搜索结果时，次低L2距离（第二相似的照片）给一个加分。加分逻辑：如果次低L2距离与最低L2距离的差 < 阈值（说明多张照片都很接近查询图），给予加分。公式：`boost_pct = max(0, min(5, (1 - (次低L2 - 最低L2) / 最低L2) × 3))`，即差距越小加分越多，封顶5个百分点
- 最终零件相似度 = `best_sim_pct + boost_pct`（封顶100%）

### 兜底硬规则

1. **类别阈值保护**：如果某零件的 best_similarity > 85%，直接前置高优先级（排在所有<85%的零件前面），不参与常规排名内卷
2. **扎堆增益封顶**：一个零件的 boost 加分不超过 5 个百分点，防止无限霸榜

### L2 距离百分比化（统计分布映射）

维护底库内所有向量间距离的统计量：
- `dist_mean` μ — 距离均值
- `dist_std` σ — 距离标准差

**公式：** `similarity% = max(0, (1 - (L2 - μ) / (3 × σ)) × 100)`

- L2=0 → 100%（完全一致）
- L2≈μ → ~50%（平均水平）
- L2≈μ+3σ → 0%（极不相似）

**增量更新：** 每次 add() 入库时，计算新向量与底库所有向量的距离，增量更新 μ 和 σ。O(n) 操作，几百条数据毫秒级完成。统计量持久化到 SQLite 中的 `stats_meta` 单行表（键值对存储 dist_mean 和 dist_std）。

## §5 前端设计

### 仓库页面

- 零件列表：每个零件一行，显示名称+类别标签+3张缩略照片+简要规格+简介
- 类别筛选 tabs（保持现有模式）
- 名称模糊搜索输入框
- 点击零件行 → 展开详情面板：所有照片大图+角度标签+完整规格key-value列表+简介+CRUD按钮
- 新增零件按钮 → 弹出表单面板
- CRUD操作：删除零件（确认对话框）、删除某照片、修改规格/简介、添加照片

### 搜索页面

- 查询输入区：保持现有上传+top_k
- 百炼判断类别标签 + 降级标识（保持）
- 结果列表：每个零件一行，显示名称+类别+相似度百分比+3张缩略照片
- 相似度百分比直接显示数值（如"78.3%"），不再用相对100%归一化
- 点击零件行 → 展开详情：所有照片+角度标签+规格+简介

### 删除路由

- 移除 `/learn` 路由
- 移除 LearnView.vue
- 导航栏从三tab变为两tab：「使用端」和「仓库」

## §6 后端实现要点

### metadata_store.py → 重构为三表管理

- 新建 `PartsStore` 类管理 parts + spec_keys 表
- 新建 `PhotosStore` 类管理 photos 表（或合并为一个 Store）
- 删除旧 metadata 表相关代码
- 增加统计量（μ, σ）的持久化读写

### vector_store.py 调整

- `category_map` 改为从 parts 表获取（通过 photo → part 查询）
- 新增 `remove_ids(ids)` 方法：软删除时重建不含这些ID的索引（IndexIDMap不支持单向量删除，需要全量重建）
- 增量更新 μ 和 σ 的方法

### pipeline.py 重构

- `learn_pipeline()` → 改为创建零件+批量照片入库
- `search_pipeline()` → 新增零件级聚合步骤：
  1. FAISS搜索照片
  2. 按part_id分组
  3. Best-of-Part计算每个零件相似度
  4. 扎堆加分
  5. 兜底硬规则排序
  6. 返回零件维度结果

### 新增路由

- `warehouse.py` 扩展为完整的 CRUD API
- 新增 `specs.py` 路由管理 spec_keys
- 删除 `learn.py` 路由

## §7 迁移方案

1. 启动时检测旧 metadata 表 → 自动迁移到 parts+photos 表
2. 迁移逻辑：按 category+specification 分组创建 part，name=specification，specs={}
3. FAISS 索引不需要重建（photo.id = 原 metadata.id）
4. 迁移完成后旧 metadata 表可选保留或删除