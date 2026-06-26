# AI 圆桌讨论 — 后端架构与数据模型

---

## 1. 项目目录结构

```
backend/
├── .env.example                  # 环境变量模板
├── requirements.txt              # Python 依赖
├── data/
│   └── roundtable.db             # SQLite 数据库文件（运行时生成）
├── tests/                        # 单元测试（待扩展）
└── app/
    ├── main.py                   # FastAPI 入口：生命周期、CORS、路由挂载
    ├── config.py                 # 配置中心：环境变量统一管理
    ├── database.py               # 异步 SQLAlchemy 引擎 + 会话工厂
    ├── exceptions.py             # 自定义异常类 + 全局异常处理器
    │
    ├── models/                   # ── 数据访问层 ──
    │   ├── __init__.py
    │   ├── session.py            # Session ORM 模型
    │   └── message.py            # Message ORM 模型
    │
    ├── schemas/                  # ── 接口表示层 ──
    │   ├── __init__.py
    │   ├── common.py             # ApiResponse[T] / PaginatedData[T]
    │   ├── guest.py              # GuestResponse
    │   ├── session.py            # SessionCreate / SessionBrief / SessionDetail
    │   └── message.py            # MessageResponse
    │
    ├── routers/                  # ── 路由控制层 ──
    │   ├── __init__.py
    │   ├── guests.py             # GET /api/experts
    │   ├── sessions.py           # POST /api/discussion/start 等 CRUD
    │   └── stream.py             # GET /api/discussion/{id}/stream (SSE)
    │
    ├── services/                 # ── 业务逻辑层 ──
    │   ├── __init__.py
    │   ├── session_service.py    # Session / Message CRUD 操作
    │   ├── prompt_manager.py     # 6位嘉宾 System Prompt + 阶段模板
    │   ├── llm_service.py        # Anthropic / OpenAI 统一调用层
    │   └── discussion_orchestrator.py  # 4阶段讨论引擎（核心编排）
    │
    └── data/
        └── guests.json           # 6位嘉宾静态数据
```

### 各模块职责速查

| 模块 | 文件 | 一句话职责 |
|------|------|-----------|
| **入口** | `main.py` | 创建 FastAPI app，注册中间件和路由，启停生命周期 |
| **配置** | `config.py` | 从 `.env` / 环境变量读取全部配置，提供 `settings` 全局单例 |
| **数据库** | `database.py` | 创建 async SQLAlchemy 引擎、会话工厂、`get_db` 依赖注入 |
| **异常** | `exceptions.py` | 定义 5 种业务异常 + 全局 FastAPI exception_handler |
| **ORM** | `models/` | 定义 `sessions` 和 `messages` 两张表的结构与关联 |
| **Schema** | `schemas/` | Pydantic 请求校验 / 响应序列化，隔离 API 契约与 DB 结构 |
| **路由** | `routers/` | 薄层，仅做参数提取和依赖注入，委托 Service 执行逻辑 |
| **服务** | `services/` | 全部业务逻辑：CRUD、LLM 调用、Prompt 构建、讨论编排 |

---

## 2. 分层架构

```
 ┌──────────────────────────────────────────────────┐
 │                   Routers (路由层)                 │
 │   参数校验、依赖注入、HTTP → Service 调用转发         │
 ├──────────────────────────────────────────────────┤
 │                  Schemas (接口层)                  │
 │   Pydantic 请求体校验 + 响应序列化 + 类型安全         │
 ├──────────────────────────────────────────────────┤
 │                  Services (业务层)                  │
 │   CRUD 操作、LLM 集成、Prompt 管理、讨论编排          │
 ├──────────────────────────────────────────────────┤
 │                  Models (数据层)                   │
 │   SQLAlchemy ORM、表结构定义、关联映射               │
 └──────────────────────────────────────────────────┘
```

**调用流向**：`HTTP Request → Router → Schema（校验）→ Service → Model（DB 操作）→ 返回`

**核心原则**：
- Router 不包含业务逻辑，只做"翻译"（HTTP ↔ Python）
- Schema 是 API 契约，与数据库 Model 解耦（两者可独立演化）
- Service 持有全部业务规则，可被多个 Router 复用
- Model 只描述数据结构，不含任何业务行为

---

## 3. 数据模型

### 3.1 数据库引擎

```python
# database.py
engine = create_async_engine(
    "sqlite+aiosqlite:///./data/roundtable.db",  # 异步 SQLite
    echo=False,                                   # DEBUG=true 时打印 SQL
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # commit 后对象仍可访问属性
)
```

| 特性 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite | 零配置、文件型、适合单机部署 |
| 驱动 | aiosqlite | 原生异步，不阻塞事件循环 |
| 会话管理 | `async_sessionmaker` | FastAPI 依赖注入，自动 commit/close |
| 建表方式 | `Base.metadata.create_all` | lifespan 启动事件中自动执行 |

---

### 3.2 Session 模型（讨论会话）

**文件**：[`app/models/session.py`](../backend/app/models/session.py)

**对应表**：`sessions`

```python
class Session(Base):
    __tablename__ = "sessions"

    id           : str       = PK, UUID, "550e8400-e29b-41d4-a716-446655440000"
    topic        : str       = TEXT, NOT NULL, "远程办公是否应该..."
    guest_ids    : str       = TEXT, NOT NULL, '["eff_expert","tech_arch","crit_thinker"]'
    status       : str       = "active" | "completed" | "error", DEFAULT 'active'
    created_at   : datetime  = UTC, NOT NULL
    completed_at : datetime  = NULL (完成时写入)
```

| 字段 | SQL 类型 | 约束 | 说明 |
|------|---------|------|------|
| `id` | `VARCHAR(36)` | PK, UUIDv4 自动生成 | 讨论唯一标识 |
| `topic` | `TEXT` | NOT NULL | 讨论话题，1-200 字符 |
| `guest_ids` | `TEXT` | NOT NULL | JSON 字符串数组，如 `["eff_expert"]` |
| `status` | `VARCHAR(20)` | DEFAULT `active` | 状态机：`active` → `completed` / `error` |
| `created_at` | `DATETIME` | NOT NULL, UTC | 创建时间 |
| `completed_at` | `DATETIME` | NULL | 完成/异常时间 |

**ORM 关联**：
```python
messages = relationship("Message", back_populates="session",
                        order_by="Message.sequence")
```
一对多：一个 Session 包含多条 Message，按 `sequence` 排序。删除 Session 时级联删除所有 Message（`ondelete="CASCADE"`）。

**状态机**：
```
active ──┬── 讨论正常结束 ──→ completed
         └── 讨论异常中断 ──→ error
```

---

### 3.3 Message 模型（发言记录）

**文件**：[`app/models/message.py`](../backend/app/models/message.py)

**对应表**：`messages`

```python
class Message(Base):
    __tablename__ = "messages"

    id           : str       = PK, UUID
    session_id   : str       = FK → sessions.id, CASCADE, NOT NULL
    phase        : str       = "opening" | "statements" | "free_discussion" | "summary"
    round        : int       = 0~3
    speaker_id   : str       = "moderator" | "eff_expert" | "prod_mgr" | ...
    speaker_name : str       = "主持人" | "效率专家" | ...
    content      : str       = TEXT, NOT NULL
    sequence     : int       = 全局序号，1 起始递增
    created_at   : datetime  = UTC
```

| 字段 | SQL 类型 | 约束 | 说明 |
|------|---------|------|------|
| `id` | `VARCHAR(36)` | PK, UUIDv4 | 消息唯一标识 |
| `session_id` | `VARCHAR(36)` | FK → sessions.id, CASCADE | 所属讨论 |
| `phase` | `VARCHAR(20)` | NOT NULL | 所处阶段枚举 |
| `round` | `INTEGER` | DEFAULT 1 | 轮次：开场/总结=0，陈述=1，讨论=2-3 |
| `speaker_id` | `VARCHAR(50)` | NOT NULL | 发言者唯一标识 |
| `speaker_name` | `VARCHAR(50)` | NOT NULL | 发言者显示名称 |
| `content` | `TEXT` | NOT NULL | 发言正文，150~500 字 |
| `sequence` | `INTEGER` | NOT NULL | 全局消息序号，决定展示顺序 |
| `created_at` | `DATETIME` | NOT NULL, UTC | 生成时间 |

**ORM 关联**：
```python
session = relationship("Session", back_populates="messages")
```
多对一：每条 Message 属于一个 Session。

**phase 枚举值**：

| 值 | 对应阶段 | round 值 |
|----|---------|---------|
| `opening` | 主持人开场 | 0 |
| `statements` | 嘉宾立场陈述 | 1 |
| `free_discussion` | 自由讨论 | 2 ~ 3 |
| `summary` | 主持人总结 | 0 |

**speaker_id 枚举值**：

| 值 | 角色 |
|----|------|
| `moderator` | 主持人 |
| `eff_expert` | 效率专家 |
| `prod_mgr` | 产品经理 |
| `tech_arch` | 技术架构师 |
| `biz_analyst` | 商业分析师 |
| `ux_designer` | 用户体验设计师 |
| `crit_thinker` | 批判性思考者 |

---

### 3.4 ER 图

```
┌──────────────────────────────┐
│           sessions            │
├──────────────────────────────┤
│ id          VARCHAR(36) PK   │
│ topic       TEXT NOT NULL    │
│ guest_ids   TEXT NOT NULL    │──── JSON: ["eff_expert", ...]
│ status      VARCHAR(20)      │──── active / completed / error
│ created_at  DATETIME         │
│ completed_at DATETIME        │
└──────────┬───────────────────┘
           │ 1
           │
           │ N
┌──────────┴───────────────────┐
│           messages            │
├──────────────────────────────┤
│ id          VARCHAR(36) PK   │
│ session_id  VARCHAR(36) FK   │──→ sessions.id (CASCADE)
│ phase       VARCHAR(20)      │
│ round       INTEGER          │
│ speaker_id  VARCHAR(50)      │
│ speaker_name VARCHAR(50)     │
│ content     TEXT NOT NULL    │
│ sequence    INTEGER          │──── 全局排序
│ created_at  DATETIME         │
└──────────────────────────────┘
```

---

## 4. 配置管理

**文件**：[`app/config.py`](../backend/app/config.py)

所有配置通过 `Settings` 类统一管理，在模块导入时自动调用 `load_dotenv()` 加载 `.env` 文件。

```python
class Settings:
    # ── 应用 ──
    APP_NAME: str     = "AI Roundtable"
    APP_VERSION: str  = "0.1.0"
    DEBUG: bool       = False

    # ── 数据库 ──
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/roundtable.db"

    # ── LLM ──
    LLM_PROVIDER: str         = "anthropic"         # "anthropic" | "openai"
    ANTHROPIC_API_KEY: str    = ""                   # 从环境变量读取
    ANTHROPIC_BASE_URL: str   = "https://api.anthropic.com"
    ANTHROPIC_MODEL: str      = "claude-sonnet-4-6"
    OPENAI_API_KEY: str       = ""
    OPENAI_BASE_URL: str      = "https://api.openai.com/v1"
    OPENAI_MODEL: str         = "gpt-4o-mini"

    # ── 讨论 ──
    FREE_DISCUSSION_ROUNDS: int = 2                  # 自由讨论轮数

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
```

**配置环境变量映射**：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_PROVIDER` | `anthropic` | 切换 LLM 厂商 |
| `ANTHROPIC_API_KEY` | — | Anthropic API 密钥 |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | 支持自定义代理 |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | 模型 ID |
| `OPENAI_API_KEY` | — | OpenAI API 密钥 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型 ID |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/roundtable.db` | 数据库路径 |
| `FREE_DISCUSSION_ROUNDS` | `2` | 自由讨论轮数 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许的前端源 |

---

## 5. 请求生命周期

以 `POST /api/discussion/start` 为例：

```
1. HTTP Request
   │  POST /api/discussion/start
   │  Body: {"topic":"...", "guest_ids":[...]}
   ▼
2. FastAPI 路由匹配
   │  routers/sessions.py → create_session()
   │  依赖注入: get_db() → AsyncSession
   ▼
3. Pydantic 校验
   │  SessionCreate: topic (1-200字), guest_ids (恰好3个不重复)
   │  失败 → 400 VALIDATION_ERROR
   ▼
4. 业务校验
   │  检查 guest_ids 是否都是合法嘉宾 ID
   │  失败 → 400 VALIDATION_ERROR
   ▼
5. Service 层
   │  session_service.create_session()
   │  → 生成 UUID, guest_ids 序列化为 JSON
   │  → INSERT INTO sessions
   ▼
6. 响应构建
   │  SessionDetail 序列化 session + guests
   ▼
7. HTTP Response
   │  201 Created
   │  {"code":0, "data": {"id":"...", "status":"active", ...}}
```

---

## 6. 模块依赖图

```
main.py
  ├── config.py          (settings 全局单例)
  ├── database.py         (engine, async_session)
  ├── exceptions.py       (AppException 体系)
  └── routers/
        ├── guests.py ──────── schemas/guest.py, data/guests.json
        ├── sessions.py ────── schemas/session.py, services/session_service.py
        └── stream.py ──────── services/discussion_orchestrator.py
                                    ├── services/llm_service.py
                                    │     └── config.py (API keys)
                                    ├── services/prompt_manager.py
                                    │     └── 6 位嘉宾 System Prompt
                                    └── services/session_service.py
                                          └── models/ (Session, Message)
```

**依赖方向**（单向、无循环）：
```
routers → schemas → services → models → database
                              → config
```

---

## 7. 异常处理体系

**文件**：[`app/exceptions.py`](../backend/app/exceptions.py)

```python
AppException (基类)
  ├── ValidationException    → 400  # 参数校验失败
  ├── NotFoundException      → 404  # 资源不存在
  ├── ConflictException      → 409  # 状态冲突（如删除进行中的讨论）
  └── LLMAPIException        → 500  # LLM API 调用失败
```

全局异常处理器：
```python
app.add_exception_handler(AppException, app_exception_handler)
```

任何抛出 `AppException` 子类的代码都会被自动捕获，返回统一格式：
```json
{
  "code": 1,
  "message": "VALIDATION_ERROR",
  "data": { "detail": "无效的嘉宾 ID: xxx" }
}
```

---

## 8. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 数据库 | SQLite + aiosqlite | 零配置部署，异步不阻塞 |
| guest_ids 存储 | JSON 字符串 | SQLite 不支持数组类型，JSON 序列化灵活 |
| 消息与阶段 | 同一张 `messages` 表 | 避免多态表，简化查询和排序 |
| LLM Provider | 策略模式 (`LLM_PROVIDER` 切换) | 同时支持 Anthropic 和 OpenAI，便于切换/测试 |
| SSE 实现 | `StreamingResponse` + async generator | 原生 FastAPI 支持，无需额外依赖 |
| 全局单例 | `get_llm_service()` | 复用 httpx 连接池，避免重复建立 TCP 连接 |
| 模型/Schema 分离 | Pydantic ↔ SQLAlchemy 各自独立 | API 契约与 DB 结构可独立演化 |
| 路由前缀 | `/api`（无版本号） | 早期项目，版本号在需要时再加 |

---

> 📌 本文档与 [SPEC.md](../SPEC.md)、[API_DESIGN.md](API_DESIGN.md) 配套使用。本文档侧重后端内部实现细节，API_DESIGN.md 侧重外部接口契约。
