# AI 圆桌讨论 — 工程范式与阶段拆解

---

## 0. 技术栈与架构决策

### 0.1 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| **前端框架** | React 19.2 + TypeScript 6.0 | 最擅长的 UI 框架；TS 提供端到端类型安全 |
| **构建工具** | Vite 8.1 | 毫秒级 HMR，原生 ESM，零配置 TS/JSX |
| **样式系统** | Tailwind CSS 4.3 | 原子化 CSS，快速迭代 UI，无独立 CSS 文件 |
| **路由** | react-router-dom 7 | SPA 路由标准，4 条路由即可覆盖全部页面 |
| **状态管理** | React Context + useReducer | 状态仅限直播间页面，无需 Redux/Zustand |
| **实时通信** | EventSource (SSE) | 浏览器原生 API，零依赖，自动重连 |
| **后端框架** | FastAPI (Python 3.13) | 原生 async/await，自动 OpenAPI 文档，SSE StreamingResponse |
| **AI 编排** | LangGraph 1.2 | StateGraph 管理复杂讨论状态机，支持 astream 流式输出 |
| **LLM 接入** | langchain-openai + httpx | ChatOpenAI 接入 DeepSeek/OpenAI；httpx 接入 Anthropic |
| **数据库** | SQLite + aiosqlite + SQLAlchemy 2.0 | 零配置、文件型，async ORM 不阻塞事件循环 |
| **测试** | pytest + pytest-asyncio + httpx | 异步测试全覆盖，ASGITransport 无需真实 HTTP |

### 0.2 前后端分离架构

```
┌──────────────────────────────┐    ┌──────────────────────────────────────┐
│  Frontend (localhost:5173)   │    │  Backend (localhost:8000)             │
│                              │    │                                      │
│  React 19 + Vite 8           │    │  FastAPI + LangGraph                 │
│  Tailwind CSS 4              │    │  SQLAlchemy 2.0 + SQLite             │
│  EventSource (SSE)           │    │  StreamingResponse (SSE)             │
│                              │    │                                      │
│  ┌──────────────────────┐    │    │  ┌────────────────────────────────┐  │
│  │ API Key: NEVER stored │    │    │  │ .env: ANTHROPIC_API_KEY       │  │
│  │ in browser           │    │    │  │       DEEPSEEK_API_KEY         │  │
│  └──────────────────────┘    │    │  │       (backend only)           │  │
│                              │    │  └────────────────────────────────┘  │
└──────────────────────────────┘    └──────────────────────────────────────┘
```

### 0.3 项目规模

| 指标 | 数量 |
|------|------|
| 后端源文件 | 15 个 |
| 前端源文件 | 15 个 |
| 测试文件 | 5 个（52 个测试用例） |
| 文档 | 5 份（SPEC + API + 后端 + 前端 + 工程） |
| LangGraph 节点 | 4 个（init → host_intro → autonomous_discussion → host_summary） |
| SSE 事件类型 | 12 种 |
| API 端点 | 6 个 |
| 数据库表 | 2 张（sessions + messages） |

---

## 1. 阶段一：SDD（Spec/Schema-Driven Development）

> **目标**：在写任何业务逻辑之前，精确定义数据模型与 API 契约，以结构化文档驱动实现，消除 AI 幻觉空间。

### 1.1 产出物

| 产出 | 文件 | 作用 |
|------|------|------|
| **需求规格** | [SPEC.md](../SPEC.md) | 业务需求唯一真相源：用户故事、嘉宾定义、讨论流程、非功能性需求 |
| **API 契约** | [docs/API_DESIGN.md](API_DESIGN.md) | 6 个端点的请求/响应/错误码/SSE 事件类型完整定义 |
| **数据模型** | [docs/BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) §3 | Session + Message 两张表的 ER 图、字段约束、状态机 |
| **Pydantic Schema** | `backend/app/schemas/` | 8 个 Pydantic 模型，编译时校验 API 契约 |
| **TypeScript 类型** | `frontend/src/types/index.ts` | 18 个 TS 接口，编译时校验前后端类型一致性 |

### 1.2 数据模型（核心实体）

```
sessions (讨论会话)                messages (发言记录)
┌──────────────────────┐          ┌──────────────────────────┐
│ id        VARCHAR PK │──┐       │ id           VARCHAR PK  │
│ topic     TEXT       │  │       │ session_id   VARCHAR FK  │──→ sessions.id
│ guest_ids TEXT(JSON) │  │       │ phase        VARCHAR     │   (CASCADE)
│ status    VARCHAR    │  │       │ round        INTEGER     │
│ created_at DATETIME  │  │       │ speaker_id   VARCHAR     │
│ completed_at DATETIME│  │       │ speaker_name VARCHAR     │
└──────────────────────┘  │       │ content      TEXT        │
                           │       │ sequence     INTEGER     │
                           │       │ created_at   DATETIME    │
                           └───────└──────────────────────────┘
```

### 1.3 API 契约（v3 最终版）

| 方法 | 路径 | 请求 Schema | 响应 Schema |
|------|------|------------|------------|
| `GET` | `/api/experts` | — | `ApiResponse<GuestResponse[]>` |
| `POST` | `/api/discussion/generate-guests` | `{topic, expert_count}` | `ApiResponse<GuestGenerateResponse>` |
| `POST` | `/api/discussion/start` | `{topic, host, experts[]}` | `ApiResponse<SessionDetail>` |
| `GET` | `/api/discussion/{id}/stream` | path param | `text/event-stream` (12 种事件) |
| `GET` | `/api/discussions` | `?page&page_size&status_filter` | `ApiResponse<PaginatedData<SessionBrief>>` |
| `DELETE` | `/api/discussions/{id}` | path param | `ApiResponse<null>` |

### 1.4 SSE 事件契约

```typescript
type SSEEventType =
  | 'connected'           // 连接建立
  | 'phase_start'         // 阶段开始 {phase, round, label}
  | 'moderator_opening'   // 主持人开场 {speaker_id, speaker_name, content}
  | 'free_discussion'     // 专家发言 {speaker_id, speaker_name, content}
  | 'moderator_summary'   // 主持人总结 {speaker_id, speaker_name, content}
  | 'expert_status'       // 专家状态更新 {status: {[id]: {state, focus}}}
  | 'consensus_update'    // 共识/分歧更新 {new_consensus, new_divergence}
  | 'phase_end'           // 阶段结束 {phase}
  | 'session_end'         // 讨论结束 {session_id, consensus, divergence}
  | 'done'                // 流关闭
  | 'error';              // 错误 {code, message}
```

---

## 2. 阶段二：DDD（Design-Driven Development）

> **目标**：以"AI 圆桌演播厅"的视觉沉浸感驱动前端组件架构、状态流转、CSS 动画设计。使用 Tailwind CSS 原子化样式 + CSS 关键帧动画实现广播级视觉效果。

### 2.1 设计语言

| 要素 | Token | 设计意图 |
|------|-------|---------|
| **主背景** | `slate-950` (#020617) | 接近纯黑，模拟演播厅暗场 |
| **次背景** | `slate-900/80` + `backdrop-blur-md` | 毛玻璃导航栏 |
| **ON AIR 指示** | `bg-red-500` + `animate-pulse` + `on-air-dot` 动画 | 广播级直播状态指示 |
| **专家状态** | 4 态：slate(待机) → yellow pulse(准备) → emerald(就绪) → blue glow(发言中) | 实时可视化 Agent 运行状态 |
| **消息气泡** | 左彩色边框(专家专属色) + 琥珀色左边框(主持人) | 一眼区分发言人角色 |
| **共识/分歧** | emerald(共识) / orange(分歧) 双色体系 | 语义化色彩编码 |
| **扫描线** | `repeating-linear-gradient` + 8s 动画 | 模拟专业演播设备扫描效果 |
| **消息入场** | `slideIn` 0.4s ease-out | 流畅的消息出现动效 |

### 2.2 演播厅布局（三栏响应式）

```
┌──────────────────────────────────────────────────────────────┐
│  ● ON AIR  │ 远程办公是否应该成为...  │ ⚡张明 🏗️李婷 🔍王刚  │  ← Header
├────────────┬─────────────────────────────────┬───────────────┤
│ 专家状态    │         Transcript              │  实时追踪      │
│            │                                 │               │
│ ● 张明     │ 🎤 主持人开场                    │ ✅ 共识        │
│   AI战略   │ 今天我们讨论...                   │ · 提升效率     │
│   发言中    │                                 │               │
│            │ 💼 张明（AI战略顾问）             │ ⚡ 分歧        │
│ ○ 李婷     │ 从技术演进看，AI将替代...         │ · 管理难度     │
│   聆听中    │                                 │               │
│            │ 📊 李婷（劳动经济学家）            │               │
│ ○ 王刚     │ 我补充一个数据：过去20年...        │               │
│   准备中    │                                 │               │
├────────────┴─────────────────────────────────┴───────────────┤
│  💬 深度讨论中 · 14 条发言              [⏹ 离开]             │  ← Footer
└──────────────────────────────────────────────────────────────┘

响应式断点:
  < 1024px: 隐藏双侧边栏，仅显示 Transcript
  > 1536px: 侧边栏扩宽至 220px/256px，Transcript 居中最大 900px
```

### 2.3 组件树

```
App
├── Navbar (毛玻璃，sticky)
└── <Routes>
    ├── HomePage                     ← 3 步流程
    │   ├── ActiveSessionsList       (进行中讨论列表)
    │   └── NewDiscussionFlow
    │       ├── TopicInput            (话题 + 专家人数)
    │       ├── GenerateButton        (调用 LLM 生成阵容)
    │       ├── GuestPreviewCards     (确认/重新生成)
    │       └── StartButton           (进入演播厅)
    │
    ├── RoundtablePage
    │   └── RoundtableProvider (Context + useReducer)
    │       └── RoundtableRoom        ← 演播厅主容器
    │           ├── HeaderBar         (ON AIR + 嘉宾 chip)
    │           ├── ExpertSidebar     (独立滚动，4态指示灯)
    │           ├── Transcript        (独立滚动，消息气泡列表)
    │           │   └── MessageBubble × N  (彩色左边框 + 标题)
    │           ├── ConsensusSidebar  (独立滚动，实时共识/分歧)
    │           └── BottomBar         (状态 + 离开按钮)
    │
    ├── HistoryPage                  ← 分页列表
    └── HistoryDetailPage            ← 静态回放 (复用 PhaseSection)
```

### 2.4 关键动画

| 动画 | 触发条件 | CSS |
|------|---------|-----|
| **消息入场** | 新消息到达 | `slideIn` 0.4s ease-out |
| **发言呼吸灯** | 某专家正在发言 | `breathe` 2s infinite (蓝) / `breathe-moderator` (金) |
| **ON AIR 脉冲** | 讨论进行中 | `onAirPulse` 1.5s ease-in-out |
| **准备中闪烁** | 专家 LLM 决策中 | `statusPulse` 0.8s infinite |
| **扫描线** | 演播厅背景 | `scanLine` 8s linear infinite |
| **状态切换** | idle/ready/speaking | `transition-all duration-300` |

---

## 3. 阶段三：TDD（Test-Driven Development）

> **目标**：对核心业务逻辑编写测试先行，以可验证的正确性保障讨论引擎质量。

### 3.1 测试分层

```
┌─────────────────────────────────────────┐
│  E2E Tests (test_api.py)               │  ← 11 tests: 完整 API 流程
│  HTTP 请求 → FastAPI → DB → 响应        │
├─────────────────────────────────────────┤
│  Service Tests (3 files)               │  ← 39 tests: 核心逻辑
│  Prompt 构建 / JSON 解析 / 调度算法      │
├─────────────────────────────────────────┤
│  Schema Tests                          │  ← 2 tests: Pydantic 校验
│  数据契约编译时+运行时双重验证            │
└─────────────────────────────────────────┘
```

### 3.2 测试清单

#### test_guest_generation.py（14 tests）

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestGuestGenerationPrompt` | 6 | 验证 Prompt 包含话题、人数、JSON 格式要求、颜色调色板、立场多样性、emoji |
| `TestGuestResponseParsing` | 10 | 有效 JSON 解析、ID 自动分配、缺失 avatar fallback、截断多余专家、Markdown 包裹处理、异常输入报错 |
| `TestGeneratedGuestSchema` | 3 | Pydantic 必填字段校验、响应结构完整性 |

#### test_speech_scheduling.py（17 tests）

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestExpertSystemPrompt` | 4 | System Prompt 包含姓名/Title/立场、鼓励自主发言、限制 1-2 句、反对空话 |
| `TestExpertDecidePrompt` | 3 | 决策 Prompt 的 JSON 结构、话题注入、Transcript 注入 |
| `TestUrgencyBasedSelection` | 5 | 最高 urgency 胜出、低于 5 不选、无人愿说、同分策略、空队列处理 |
| `TestJSONParsing` | 5 | 纯净 JSON、Markdown 包裹、混杂文本、异常 fallback、空 content 处理 |
| `TestTranscriptFormatting` | 3 | 发言人名称包含、截断到 last_n、空列表 |

#### test_consensus.py（10 tests）

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestConsensusCheckPrompt` | 5 | Prompt 包含话题、Transcript、已有共识/分歧、JSON 要求、字数限制 |
| `TestConsensusParsing` | 3 | 新增共识解析、共识+分歧同时、空结果处理 |
| `TestConsensusAccumulation` | 3 | 跨轮累计、去重逻辑、字数验证 |

#### test_api.py（11 tests）

| 测试类 | 测试数 | 覆盖内容 |
|--------|--------|---------|
| `TestGuestListAPI` | 2 | GET /api/experts 返回 6 位嘉宾 + 字段完整性 |
| `TestSessionCRUD` | 5 | 创建/详情/列表/删除(409)/健康检查 |
| `TestMultiSessionIsolation` | 2 | 不同 session ID 隔离、active 筛选 |
| `TestValidation` | 2 | 空 topic 422、专家数不足 422 |

### 3.3 测试基础设施

```python
# conftest.py — 核心 Fixture
@pytest_asyncio.fixture
async def async_client():
    """每次测试独立的 SQLite 数据库 + ASGI 传输层"""
    1. 创建新表 (Base.metadata.create_all)
    2. 创建 ASGITransport(app) 避免真实 HTTP
    3. yield AsyncClient
    4. 销毁表 (Base.metadata.drop_all) 保证隔离
```

---

## 4. Git 提交历史（工程阶段映射）

```
f8d991c  TDD+DDD: 50 core tests + immersive studio UI + responsive layout
8dfe9d5  v3: Autonomous AI Roundtable -- dynamic guests, expert self-selection
77250d4  feat: 前端 React + Tailwind 完整代码
6ca0271  后端
e55dd70  docs: 添加需求规格文档 SPEC.md
```

| Commit | 阶段 | 核心动作 |
|--------|------|---------|
| `e55dd70` | **SDD** | SPEC.md 需求规格定义 |
| `6ca0271` | **SDD** | 后端数据模型 + API 契约 + FastAPI 脚手架 |
| `77250d4` | **DDD** | 前端 React 组件 + Tailwind 样式 + SSE 消费 |
| `8dfe9d5` | **DDD** | LangGraph 自主讨论引擎 + 动态嘉宾生成 + 专家状态窗 |
| `f8d991c` | **TDD** | 50 个测试 + 演播厅沉浸式 UI + 响应式布局 |

---

## 5. Superpowers / Claude Code 协同范式

本项目全程使用 Claude Code 作为唯一开发环境。以下是 AI 协同的关键模式：

### 5.1 结构化 Prompt 工程

```
用户 Prompt 模式:
  1. 先定义输出格式（"写进 md 文档"、"以 JSON 格式"）
  2. 再列出功能清单（编号列表）
  3. 最后给出约束条件（"禁止 JSON 原文显示在页面上"）

AI 输出模式:
  1. 先读取相关文件验证现状
  2. 再规划改动范围
  3. 最后并行写入所有文件
  4. 完成后验证编译 + 运行测试
```

### 5.2 上下文管理

| 手段 | 效果 |
|------|------|
| SPEC.md 作为唯一真相源 | 每次改动前引用 SPEC，避免需求漂移 |
| `docs/` 目录 5 份文档 | 不同类型信息物理隔离，AI 可按需检索 |
| 每次完成自动 git commit | 回滚粒度细，AI 可在任意 commit 基础上继续 |
| TodoWrite 跟踪任务 | 多步骤任务不遗漏，用户可随时了解进度 |

### 5.3 验证闭环

```
文件写入 → Edit/Write
    ↓
编译验证 → tsc --noEmit / python -c "import..."
    ↓
测试验证 → pytest -q
    ↓
接口验证 → urllib 发起 HTTP 请求
    ↓
Git 提交 → 带描述的 commit
```

---

> 📌 本文档为 AI Roundtable 项目的工程方法论总结。与 SPEC.md（需求）、API_DESIGN.md（契约）、BACKEND_ARCHITECTURE.md（后端实现）、FRONTEND_ARCHITECTURE.md（前端实现）配套构成完整的项目知识库。
