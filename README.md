# 求职岗位 API

求职实习平台后端服务，基于 FastAPI 框架开发，提供实习岗位浏览、用户登录、收藏管理和浏览历史等功能。

## 技术栈

- **Python 3.12**
- **FastAPI**
- **SQLAlchemy 2.0**
- **MySQL** 
- **Redis**
- **Docker**

## **项目结构**

```
job-api/
│
├── config/                  # 配置层
│   ├── __init__.py
│   ├── db_config.py        # 数据库连接配置（异步引擎、会话工厂、依赖注入）
│   └── redis_config.py      
│
├── models/                  # ORM 模型层（对应数据库表结构）
│   ├── __init__.py			# ORM 模型基类 / TimestampMixin 时间戳类
│   ├── internship.py        # Internship 实习岗位表、InternshipCategory 分类表
│   ├── users.py             # User 表 / UserToken 表
│   ├── collects.py          # Collect 收藏表
│   └── historys.py          # ViewHistory 浏览历史表
│
├── schemas/                 # Pydantic 模型层（请求/响应数据校验）
│   ├── __init__.py			# 通用响应模型 ApiResponse
│   ├── collects.py          # 收藏列表里，单个岗位的响应模型 CollectInternshipInfo
│   ├── historys.py          # 浏览历史中每一项的响应模型 HistoryItemResponse
│   ├── internship.py        # 实习岗位相关 Pydantic：分类、列表、详情、分页响应
│   └── users.py             # 用户相关：注册、登录、修改密码、更新个人信息、查看个人信息
│
├── routers/                 # 路由层（API 接口定义）
│   ├── __init__.py
│   ├── internship.py        # /api/internship — 实习岗位分类、列表、详情、相关推荐
│   ├── users.py             # /api/user — 注册、登录、用户信息、修改个人资料、修改密码
│   ├── collects.py          # /api/collects — 收藏 / 取消收藏、列表、清空
│   ├── historys.py          # /api/history — 添加、获取历史记录、删除单/多条、清空
│   └── ai_assistant.py      # /api/ai — AI助手聊天接口
│
├── crud/                    # 数据操作层（数据库 CRUD 封装）
│   ├── __init__.py
│   ├── internship.py        # 实习岗位查询、浏览量更新、相关推荐
│   ├── users.py             # 用户注册 / 查询、认证、Token 管理、信息更新
│   ├── collects.py          # 收藏增删查
│   └── historys.py          # 历史记录增删查、清空
│
├── services/                # 业务逻辑与缓存层
│   ├── __init__.py
│   ├── cache_service.py     # 重写 redis 类，添加自增方法用于计数
│   ├── view_counter_service.py 
│   └── deepseek_service.py  # DeepSeek API 封装，含岗位数据注入和关键词提取
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── auth.py              # Token 认证依赖注入（get_current_user）
│   └── security.py          # 密码加密与验证（bcrypt）
│
├── main.py                  # 应用入口
├── dependencies.py          # 依赖注入与后台任务管理
├── fetch_job.py             # 岗位数据爬取脚本
├── import_data.py           # 数据导入脚本
├── requirements.txt         # 项目依赖
├── pyproject.toml           # 项目配置
├── docker-compose.yml
├── Dockerfile
├── .env
└── .gitignore
```

## 运行项目

```bash
# 确保虚拟环境已激活
.\.venv\Scripts\Activate
```

## API 文档

项目启动后，浏览器访问以下地址查看自动生成的交互式 API 文档：

- **Swagger UI**：`http://127.0.0.1:8000/docs`
- **ReDoc**：`http://127.0.0.1:8000/redoc`

在 Swagger UI 中可以直接测试每个接口，包括需要 Token 认证的接口（点击 Authorize 按钮输入 Token）。

## API 接口总览

### 实习岗位模块 `/api/internship`

| 方法 | 路径 | 说明 | 是否需要登录 |
|------|------|------|:------:|
| GET | `/api/internship/categories` | 获取岗位分类列表 | 否 |
| GET | `/api/internship/list?categoryId=&province=&education=&page=&pageSize=` | 获取岗位列表（分页） | 否 |
| GET | `/api/internship/detail?id=` | 获取岗位详情（浏览量+1） | 否 |

### 用户模块 `/api/user`

| 方法 | 路径 | 说明 | 是否需要登录 |
|------|------|------|:------:|
| POST | `/api/user/register` | 用户注册 | 否 |
| POST | `/api/user/login` | 用户登录 | 否 |
| GET | `/api/user/profile` | 获取当前用户信息 | 是 |
| PATCH | `/api/user/profile` | 修改用户信息 | 是 |
| PUT | `/api/user/password` | 修改密码 | 是 |

### 收藏模块 `/api/collects`

| 方法 | 路径 | 说明 | 是否需要登录 |
|------|------|------|:------:|
| GET | `/api/collects/list` | 获取收藏列表 | 是 |
| POST | `/api/collects/toggle/{internship_id}` | 收藏/取消收藏切换 | 是 |
| DELETE | `/api/collects/delete` | 清空收藏列表 | 是 |

### 浏览历史模块 `/api/history`

| 方法 | 路径 | 说明 | 是否需要登录 |
|------|------|------|:------:|
| POST | `/api/history/record/{internship_id}` | 添加浏览历史 | 是 |
| GET | `/api/history/list` | 获取历史列表 | 是 |
| DELETE | `/api/history/{record_id}` | 删除单条历史 | 是 |
| DELETE | `/api/history/` | 清空全部历史 | 是 |

### AI助手模块 `/api/ai`

| 方法 | 路径 | 说明 | 是否需要登录 |
|------|------|------|:------:|
| POST | `/api/ai/chat` | 与AI助手聊天 | 是 |

**聊天请求参数：**
```json
{
  "message": "北京有哪些开发岗位？",
  "conversation_history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！我是实习帮助手..."}
  ]
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
      {"id": 1, "title": "前端开发实习生", "company_name": "...", "salary_min": 8, "salary_max": 15, "province": "北京", "education": "本科"}
    ]
  }
}
```

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

## 缓存策略

项目使用 Redis 作为缓存层，减少数据库查询压力，各类型数据的缓存过期时间不同：

| 数据类型 | 缓存 Key 格式 | 过期时间 |
|----------|--------------|---------|
| 岗位分类 | `internship:categories:list` | 24 小时 |
| 岗位浏览量 | `internship:views:{岗位ID}` | 60 秒刷盘 |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `user` | 用户信息（用户名、密码、头像、性别等） |
| `user_token` | 用户登录令牌（UUID，7天过期） |
| `internship_category` | 实习岗位分类 |
| `internship` | 实习岗位（标题、公司、薪资、学历要求等） |
| `internship_collect` | 收藏记录（用户 + 岗位唯一约束） |
| `internship_view_history` | 浏览历史（重复浏览更新时间） |

数据库表由 SQLAlchemy ORM 模型自动创建，启动时会检查并创建缺失的表。

## 全局异常处理

项目注册了多层异常处理器，从具体到通用逐级捕获：

1. `HTTPException` — 业务层主动抛出的异常（如参数校验失败、资源不存在）
2. `IntegrityError` — 数据库完整性约束错误（用户名重复、外键关联不存在等）
3. `SQLAlchemyError` — 其他数据库操作错误（连接失败、查询语法错误等）
4. `Exception` — 兜底，捕获所有未处理的异常

所有异常统一返回标准 JSON 格式，包含错误码、错误信息和空数据字段，便于前端统一处理。
