# 实习帮 - 高校实习岗位平台

求职实习平台后端服务（核心），基于 FastAPI 框架开发，提供实习岗位浏览、用户登录、收藏管理、浏览历史和 **AI 助手（Agent 循环 + RAG 检索增强）** 等功能。仓库内附带一个基于 Vue 3 + Element Plus（CDN 方式）的前端演示页面，仅作接口联调与功能展示用途。

## 技术栈

### 后端

- **Python 3.11**
- **FastAPI**（异步 API）
- **SQLAlchemy 2.0**（异步 ORM）
- **MySQL 8.0**
- **Redis Stack**（`redis/redis-stack-server`，带 RediSearch 模块，用于缓存、限流、浏览量计数、会话存储与**向量检索**）
- **OpenAI SDK**（兼容调用 DeepSeek 大模型，支持 Function Calling）
- **Sentence-Transformers**（`BAAI/bge-small-zh-v1.5`，512 维中文 Embedding 模型）
- **Numpy / Pandas**（向量计算与批量灌库）
- **Docker / Docker Compose**（四容器编排：app + mysql + redis + nginx）

### 前端（演示用）

- **Vue 3**（CDN，Composition API）
- **Element Plus**（CDN，UI 组件库）
- **Fetch API**（HTTP 请求）

## 项目结构

```
job-api/
│
├── config/                  # 配置层
│   ├── __init__.py         # 全局常量（如语义检索相似度阈值 SCORE_THRESHOLD）
│   ├── db_config.py        # 数据库连接配置（异步引擎、会话工厂、依赖注入）
│   └── redis_config.py     # Redis 连接池配置
│
├── core/                    # 核心抽象层
│   ├── __init__.py
│   └── tool.py             # Tool 工具类（封装名称/描述/参数schema/执行函数，可输出 OpenAI Function Calling schema）
│
├── models/                  # ORM 模型层（对应数据库表结构）
│   ├── __init__.py         # ORM 基类 Base / TimestampMixin 时间戳混入
│   ├── internship.py       # Internship 实习岗位表、InternshipCategory 分类表
│   ├── users.py            # User 表 / UserToken 表
│   ├── collects.py         # Collect 收藏表（user_id+internship_id 复合唯一约束）
│   └── historys.py         # ViewHistory 浏览历史表
│
├── schemas/                 # Pydantic 模型层（请求/响应数据校验）
│   ├── __init__.py         # 通用响应模型 ApiResponse、BaseSchema
│   ├── ai_assistant.py     # AI 助手请求/响应模型（ChatRequest / ChatResponse / RelatedJob）
│   ├── collects.py         # CollectInternshipInfo 收藏列表项
│   ├── historys.py         # HistoryItemResponse 浏览历史项
│   ├── internship.py       # 分类 / 列表 / 详情 / 分页响应
│   └── users.py            # 注册 / 登录 / 修改密码 / 个人信息
│
├── routers/                 # 路由层（API 接口定义）
│   ├── __init__.py
│   ├── internship.py       # /api/internship — 分类、列表、详情、相关推荐
│   ├── users.py            # /api/user — 注册、登录、用户信息、改密
│   ├── collects.py         # /api/collects — 收藏切换、列表、清空
│   ├── historys.py         # /api/history — 记录、列表、删除单/全、清空
│   └── ai_assistant.py     # /api/ai — AI 助手多轮对话（Agent + RAG）
│
├── crud/                    # 数据操作层（数据库 CRUD 封装）
│   ├── __init__.py
│   ├── internship.py       # 实习岗位查询、浏览量刷盘、相关推荐、语义搜索辅助
│   ├── users.py            # 用户注册/查询、认证、Token 管理
│   ├── collects.py         # 收藏增删查
│   └── historys.py         # 历史记录增删查、清空
│
├── services/                # 业务逻辑与缓存层
│   ├── __init__.py
│   ├── cache_service.py         # Redis 封装（自增计数原子操作）
│   ├── view_counter_service.py  # 浏览量计数 + 定时刷盘
│   ├── session_manager.py       # 会话管理器（多轮对话历史持久化到 Redis）
│   ├── tool_functions.py        # Agent 工具函数实现（含 RAG 语义检索）
│   └── deepseek_service.py     # DeepSeek 大模型封装 + Agent 循环
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── auth.py             # Token 认证依赖（get_current_user）
│   ├── http.py             # HTTP 相关工具
│   ├── rate_limit.py       # 基于 Redis 的 IP / 用户频率限制
│   └── security.py         # 密码加密与验证（bcrypt）
│
├── scripts/                 # 一次性运维脚本
│   └── embed_jobs_from_csv.py  # 岗位向量化灌库脚本（CSV → Embedding → Redis 向量索引）
│
├── deploy/                  # 中间件部署配置
│   └── redis/
│       └── redis.conf      # Redis Stack 配置（加载 RediSearch 模块、AOF 持久化、内存上限）
│
├── nginx/                   # Nginx 反向代理配置
│   └── nginx.conf          # 80 端口反代到 app:8000
│
├── frontend/                # 前端演示页面（仅作联调展示，非核心）
│   ├── index.html          # 单页入口（岗位大厅 / 收藏 / 历史 / 详情弹窗 / AI 助手）
│   ├── css/style.css       # 自定义样式
│   └── js/
│       ├── api.js          # Fetch API 封装（自动携带 Token / 错误处理）
│       └── app.js          # Vue 3 + Element Plus 应用逻辑
│
├── logs/                    # 应用日志目录（按日滚动，保留 10 天）
├── main.py                  # 应用入口（路由挂载 / 异常处理 / 静态文件 / /health）
├── dependencies.py          # 后台任务（浏览量刷盘）生命周期管理
├── fetch_job.py             # 高校就业网岗位爬取脚本
├── import_data.py           # CSV 数据导入脚本（position_id 去重，写入 MySQL）
├── ncss_intern_jobs_*.csv   # 爬取得到的岗位原始数据
├── requirements.txt         # 项目依赖
├── pyproject.toml           # 项目元配置
├── pyrightconfig.json       # 类型检查配置
├── docker-compose.yml       # 四容器编排（app + mysql + redis + nginx）
├── Dockerfile               # FastAPI 镜像构建文件
├── .dockerignore
├── .env                     # 环境变量（不提交 Git）
└── .gitignore
```

## 运行项目

### 方式一：Docker Compose 一键启动（推荐）

适合快速部署 / 一键运行。会拉起 4 个容器：`app`（FastAPI）、`db`（MySQL）、`redis`（Redis Stack，带向量检索）、`nginx`（反向代理）。

#### 前置要求

| 工具             | 最低版本   | 说明                                                |
| -------------- | ------ | ------------------------------------------------- |
| Docker Engine  | 20.10+ | [官方安装文档](https://docs.docker.com/engine/install/) |
| Docker Compose | v2.0+  | Docker Desktop 自带；Linux 需单独安装 compose 插件          |

> macOS / Windows 用户直接安装 **Docker Desktop** 即可。

> 注意：AI 助手依赖 `BAAI/bge-small-zh-v1.5` Embedding 模型（约 95MB），首次启动或灌库时会自动从 HuggingFace 镜像下载，需保证网络可访问 `hf-mirror.com`（已在 compose 中配置 `HF_ENDPOINT`）。

#### 步骤

```bash
# 1. 克隆仓库后进入项目根目录
cd job-api

# 2. 检查并填写环境变量文件 .env（见下方「环境变量配置」）

# 3. 一键构建并启动（首次会自动拉取 mysql / redis-stack / nginx / python 镜像）
docker compose up -d --build

# 4. 访问服务（经 Nginx 反代，80 端口）
#    前端演示页：    http://localhost/
#    Swagger API：  http://localhost/docs
#    ReDoc API：    http://localhost/redoc
#    健康检查：      http://localhost/health
#  也可直连 app 容器（绕过 Nginx）：http://localhost:8000/

# 5. 导入初始数据（岗位数据）
#    5.1 导入岗位结构化数据到 MySQL（position_id 去重）
docker compose exec app python import_data.py
#    5.2 向量化灌库到 Redis（构建向量索引，AI 助手语义检索依赖此步）
docker compose exec app python scripts/embed_jobs_from_csv.py
```

启动后 MySQL 容器会等待 `db` healthcheck 通过后 `app` 才启动，无需手动等待；`app` 健康检查通过后 `nginx` 才会启动。

#### 常用命令

```bash
# 查看全部容器状态
docker compose ps

# 实时查看 app 服务日志
docker compose logs -f app

# 查看最近 100 行 mysql 日志
docker compose logs --tail 100 db

# 修改代码后，只重启 app（保留数据库）
docker compose restart app

# 修改 Dockerfile / requirements.txt 后重新构建并启动
docker compose up -d --build

# 停止所有容器（保留数据卷）
docker compose down

# 停止并清除数据卷（会清空数据库与 Redis 数据）
docker compose down -v
```

### 方式二：本地 Python 开发运行

需要本机已安装 Python 3.11+、MySQL 8.0、**Redis Stack**（需带 RediSearch 模块，普通 Redis 无法支持向量检索）。

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate     # Windows
# source .venv/bin/activate  # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 确保 MySQL 和 Redis Stack 服务已启动，.env 中连接地址指向本地（127.0.0.1）

# 4. 启动服务（带热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 5. 导入岗位数据
python import_data.py                          # 结构化数据进 MySQL
python scripts/embed_jobs_from_csv.py           # 向量化灌库进 Redis
```

### 环境变量配置（.env）

`docker-compose.yml` 通过 `env_file: .env` 读取环境变量，**不要把 .env 提交到 Git**。示例：

```dotenv
# --- MySQL ---
MYSQL_ROOT_PASSWORD=root_password_123   # root 密码（仅容器初始化用）
MYSQL_DATABASE=internship_app           # 数据库名，固定
MYSQL_USER=myuser                       # 业务用户
MYSQL_PASSWORD=123456                   # 业务用户密码

# --- 数据库连接 URL ---
# Docker Compose 方式：主机名写 "db"（compose 内部 DNS）
ASYNC_DATABASE_URL=mysql+aiomysql://myuser:123456@db:3306/internship_app?charset=utf8mb4
# 本地开发方式：主机名写 127.0.0.1
# ASYNC_DATABASE_URL=mysql+aiomysql://myuser:123456@127.0.0.1:3306/internship_app?charset=utf8mb4

# --- Redis（必须为 Redis Stack，带 RediSearch 模块）---
# Docker Compose 方式：主机名写 "redis"
REDIS_URL=redis://redis:6379/0
# 本地开发方式：主机名写 127.0.0.1
# REDIS_URL=redis://127.0.0.1:6379/0

# --- AI 服务（DeepSeek 大模型，OpenAI 兼容协议）---
# 未配置时聊天接口返回错误提示，但其他业务不受影响
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> Docker Compose 中已为 `app` 容器预设 HuggingFace 镜像相关变量：`HF_ENDPOINT=https://hf-mirror.com`、`HF_HOME=/app/.cache/huggingface`，用于加速 Embedding 模型下载。

## API 文档

项目启动后，浏览器访问以下地址查看自动生成的交互式 API 文档（经 Nginx 反代）：

- **Swagger UI**：`http://localhost/docs`
- **ReDoc**：`http://localhost/redoc`

在 Swagger UI 中可以直接测试每个接口，包括需要 Token 认证的接口（点击 Authorize 按钮输入 Token）。

## API 接口总览

### 实习岗位模块 `/api/internship`

| 方法  | 路径                                                                      | 说明            | 是否需要登录 |
| --- | ----------------------------------------------------------------------- | ------------- | :----: |
| GET | `/api/internship/categories`                                            | 获取岗位分类列表      |    否   |
| GET | `/api/internship/list?categoryId=&province=&education=&page=&pageSize=` | 获取岗位列表（分页）    |    否   |
| GET | `/api/internship/detail?id=`                                            | 获取岗位详情（浏览量+1） |    否   |

### 用户模块 `/api/user`

| 方法   | 路径                 | 说明                                          | 是否需要登录 |
| ----- | -------------------- | --------------------------------------------- | :----------: |
| POST  | `/api/user/register` | 用户注册（限流：IP 30s/5次）                  |      否      |
| POST  | `/api/user/login`    | 用户登录（限流：IP 30s/5次 + 用户名 30s/5次） |      否      |
| GET   | `/api/user/profile`  | 获取当前用户信息                              |      是      |
| PATCH | `/api/user/profile`  | 修改用户信息                                  |      是      |
| PUT   | `/api/user/password` | 修改密码                                      |      是      |

### 收藏模块 `/api/collects`

| 方法     | 路径                                     | 说明        | 是否需要登录 |
| ------ | -------------------------------------- | --------- | :----: |
| GET    | `/api/collects/list`                   | 获取收藏列表    |    是   |
| POST   | `/api/collects/toggle/{internship_id}` | 收藏/取消收藏切换 |    是   |
| DELETE | `/api/collects/delete`                 | 清空收藏列表    |    是   |

### 浏览历史模块 `/api/history`

| 方法     | 路径                                    | 说明     | 是否需要登录 |
| ------ | ------------------------------------- | ------ | :----: |
| POST   | `/api/history/record/{internship_id}` | 添加浏览历史 |    是   |
| GET    | `/api/history/list`                   | 获取历史列表 |    是   |
| DELETE | `/api/history/{record_id}`            | 删除单条历史 |    是   |
| DELETE | `/api/history/`                       | 清空全部历史 |    是   |

### AI助手模块 `/api/ai`

| 方法   | 路径             | 说明                          | 是否需要登录 |
| ---- | -------------- | ----------------------- | :----: |
| POST | `/api/ai/chat` | 与AI助手多轮对话（限流：每用户 60s/10次） |    是   |

**聊天请求参数：**

```json
{
  "message": "北京有哪些开发岗位？",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**聊天响应：**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "reply": "根据你的需求，我为你推荐以下北京地区的开发岗位：...",
    "related_jobs": [
      {
        "id": 1,
        "title": "前端开发实习生",
        "company_name": "XX科技有限公司",
        "salary_min": 8,
        "salary_max": 15,
        "province": "北京",
        "education": "本科"
      }
    ],
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

> **说明**：
> - `session_id` 为可选字段。不传（`null`）时后端会生成新的会话 ID 并返回，前端需保存以便续接多轮对话；后续请求带上同一 `session_id` 即可维持上下文。
> - 会话历史存储在 Redis（key: `ai:session:{user_id}:{session_id}`，TTL 1 小时），不依赖前端回传历史消息，避免提示注入风险。
> - `related_jobs` 可能为 `null`（AI 未调用检索工具时）或空列表（无匹配岗位）。

### 认证方式

需要登录的接口在请求头中携带 Token：

```
Authorization: Bearer <token>
```

Token 在注册或登录成功后返回，有效期 7 天。

## 统一响应格式

所有接口返回统一的 JSON 结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

分页接口的 `data` 结构：

```json
{
  "items": [],
  "total": 100,
  "has_more": true
}
```

## AI 助手架构（Agent 循环 + RAG）

AI 助手采用 **Agent 循环 + 检索增强生成（RAG）** 架构，相比直接调用大模型，能够基于平台真实的实习岗位库给出可信赖的推荐。

### 整体流程

```
用户消息 + session_id
        │
        ▼
┌──────────────────────────┐
│ SessionManager           │  从 Redis 加载多轮会话历史
│ (ai:session:{uid}:{sid}) │
└──────────────────────────┘
        │ messages（不含 system prompt）
        ▼
┌──────────────────────────┐
│ DeepSeekService.chat     │  拼装 system prompt + 历史 + 当前消息
│  ─ Agent 循环（≤5轮）    │
│    ├─ 调用 DeepSeek       │  tool_choice="auto"，模型自行决定是否调工具
│    ├─ 有 tool_calls?     │
│    │   YES → 执行工具函数 │  search_jobs_by_semantic（RAG 检索）
│    │        → 把工具结果  │
│    │          喂回模型   │
│    │        → 继续循环    │
│    │   NO  → 返回最终回复  │
└──────────────────────────┘
        │ reply, related_jobs, updated_messages
        ▼
   保存会话 + 返回前端
```

### 关键组件

| 组件 | 文件 | 职责 |
| --- | --- | --- |
| 路由入口 | [routers/ai_assistant.py](file:///d:/Dev/Projects/job-api/routers/ai_assistant.py) | 接收请求、限流、串联会话与 Agent |
| 会话管理 | [services/session_manager.py](file:///d:/Dev/Projects/job-api/services/session_manager.py) | 多轮对话历史读写，Redis 持久化，TTL 1h |
| Agent 循环 | [services/deepseek_service.py](file:///d:/Dev/Projects/job-api/services/deepseek_service.py) | 拼装 system prompt、循环调用大模型、解析 tool_calls、执行工具、回喂结果 |
| 工具抽象 | [core/tool.py](file:///d:/Dev/Projects/job-api/core/tool.py) | `Tool` 类：封装名称/描述/参数 schema/异步执行函数，可输出 OpenAI Function Calling schema |
| 工具实现 | [services/tool_functions.py](file:///d:/Dev/Projects/job-api/services/tool_functions.py) | `search_jobs_by_semantic_func`：Embedding + RediSearch KNN 向量检索 |
| 灌库脚本 | [scripts/embed_jobs_from_csv.py](file:///d:/Dev/Projects/job-api/scripts/embed_jobs_from_csv.py) | 批量将 CSV 岗位向量化并写入 Redis 向量索引 |

### RAG 检索细节

- **Embedding 模型**：`BAAI/bge-small-zh-v1.5`（512 维，中文优化），全局单例加载，避免重复初始化。
- **灌库流程**：CSV 岗位记录（岗位名称 + 专业要求 + 福利标签 + 单位名称）拼接为文本 → 批量编码为 512 维 float32 向量 → 以 `job:{职位ID}` 为 key 存入 Redis Hash。
- **向量索引**：`idx:jobs`，基于 RediSearch，使用 HNSW 算法 + COSINE 距离度量。索引字段含 `job_id`、`province`、`education`（TAG，可过滤）与 `embedding`（VECTOR）。
- **查询流程**：用户自然语言 → 编码为查询向量 → KNN 查询 `*=>[KNN {top_k} @embedding $vec AS score]` → 按相似度排序取 Top-K → 用 `SCORE_THRESHOLD`（见 `config/__init__.py`，cosine 距离越大越不相似）过滤掉不相关结果 → 返回结构化岗位列表给大模型组织回复。
- **工具注入**：Agent 仅注册一个工具 `search_jobs_by_semantic`，system prompt 引导模型在用户询问岗位时调用它，检索结果由模型直接基于真实数据回答，避免幻觉。

### Agent 循环说明

- 最大迭代 5 次（`MAX_ITERATIONS = 5`），防止模型陷入无限工具调用。
- 每轮：调用模型 → 若返回 `tool_calls` 则执行工具并把 `tool` 角色消息追加回 messages 继续循环；否则返回最终文本回复。
- 会话历史（不含 system prompt）在循环结束后统一写回 Redis，保持多轮上下文连续。

## 缓存策略

项目使用 Redis 作为缓存层，减少数据库查询压力，各类型数据的缓存过期时间不同：

| 数据类型  | 缓存 Key 格式                    | 过期时间   |
| ----- | ---------------------------- | ------ |
| 岗位分类  | `internship:categories:list` | 24 小时  |
| 岗位浏览量 | `internship:views:{岗位ID}`    | 60 秒刷盘 |
| AI 会话历史 | `ai:session:{user_id}:{session_id}` | 1 小时 |
| AI 限流计数 | `ai:rate:{user_id}` | 60 秒 |

> 向量检索数据（`job:{职位ID}` 与索引 `idx:jobs`）由灌库脚本写入并持久化（Redis AOF），不设 TTL。

## 数据库表结构

| 表名                        | 说明                   |
| ------------------------- | -------------------- |
| `user`                    | 用户信息（用户名、密码、头像、性别等）  |
| `user_token`              | 用户登录令牌（UUID，7天过期）    |
| `internship_category`     | 实习岗位分类               |
| `internship`              | 实习岗位（标题、公司、薪资、学历要求等） |
| `internship_collect`      | 收藏记录（用户 + 岗位唯一约束）    |
| `internship_view_history` | 浏览历史（重复浏览更新时间）       |

数据库表由 SQLAlchemy ORM 模型自动创建，启动时会检查并创建缺失的表。

## 全局异常处理

项目注册了多层异常处理器，从具体到通用逐级捕获：

1. `HTTPException` — 业务层主动抛出的异常（如参数校验失败、资源不存在）
2. `IntegrityError` — 数据库完整性约束错误（用户名重复、外键关联不存在等）
3. `SQLAlchemyError` — 其他数据库操作错误（连接失败、查询语法错误等）
4. `Exception` — 兜底，捕获所有未处理的异常

所有异常统一返回标准 JSON 格式，包含错误码、错误信息和空数据字段，便于前端统一处理。
