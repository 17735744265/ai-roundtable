# AI 圆桌讨论 — 需求规格文档

---

## 1. 项目概述

### 1.1 项目名称

**AI Roundtable** — AI 圆桌讨论平台

### 1.2 项目简介

AI Roundtable 是一个基于大语言模型的沉浸式圆桌讨论 Web 应用。支持两种模式：**AI 根据话题自动生成专家阵容**（用户可勾选确认），或从 6 位预设专家中**手动选择 3-6 位**。专家**自主决定发言时机**（非机械轮流），每次发言 1-2 句简洁有力。讨论共 30 轮，每轮最多 2 位专家发言，全程通过 Server-Sent Events (SSE) **逐句流式推送**，共识与分歧实时追踪。最终主持人以自然语言总结。

### 1.3 目标用户

- 需要对复杂话题获取多角度分析的决策者
- 希望通过辩论式学习加深理解的求知者
- 寻求创新思路的产品/技术团队

### 1.4 核心价值

- **多视角**：6 位专家各有独特的思维框架，避免单一视角的局限
- **结构化讨论**：四阶段流程确保讨论既有深度又有条理
- **实时体验**：逐字流式输出，模拟真人对话节奏
- **可回溯**：历史讨论记录持久化存储，随时回顾

---

## 2. 预设 AI 嘉宾

| 序号 | 角色 | 系统提示词核心 | 思维特征 |
|------|------|---------------|----------|
| 1 | **效率专家** (Efficiency Expert) | 专注于流程优化、时间管理和资源利用效率 | 关注"如何做得更快更好"，强调方法论与执行力 |
| 2 | **产品经理** (Product Manager) | 关注用户需求、市场契合度和产品价值主张 | 关注"用户要什么"，以用户故事和价值驱动思考 |
| 3 | **技术架构师** (Technical Architect) | 从系统设计、可扩展性、技术可行性角度切入 | 关注"技术上怎么实现"，注重系统边界和技术负债 |
| 4 | **商业分析师** (Business Analyst) | 以 ROI、市场规模、竞争优势为核心分析框架 | 关注"值不值得做"，强调数据驱动和商业可持续性 |
| 5 | **用户体验设计师** (UX Designer) | 以可用性、交互逻辑和用户心理模型为出发点 | 关注"用户怎么用"，强调共情、直觉和设计美学 |
| 6 | **批判性思考者** (Critical Thinker) | 挑战假设、挖掘逻辑漏洞、找出潜在风险 | 关注"这真的对吗"，被视为讨论中的魔鬼代言人 |

每位嘉宾由独立的 System Prompt 定义其角色人格，通过 LLM API 调用生成发言内容。

---

## 3. 讨论流程

### 3.1 阶段总览

```
┌──────────────┐    ┌─────────────────────────────┐    ┌──────────────┐
│  第一阶段     │ → │       第二阶段               │ → │  第三阶段     │
│  主持人开场   │    │  自主深度讨论 (30轮)          │    │  主持人总结   │
│  (~200字)    │    │  每轮最多2位专家发言            │    │  (~400字)    │
│              │    │  专家自主决定发言时机            │    │  自然语言     │
└──────────────┘    └─────────────────────────────┘    └──────────────┘
```

### 3.2 第一阶段：主持人开场

- **触发**：用户提交话题 + 选定嘉宾后自动开始
- **内容**：主持人介绍话题背景，简要介绍各位专家
- **字数**：约 80-120 字
- **SSE 事件**：`phase_start` → `moderator_opening`

### 3.3 第二阶段：自主深度讨论

- **轮次**：30 轮（可配置 `FREE_DISCUSSION_ROUNDS`）
- **发言机制**：每轮所有专家并发 LLM 决策是否发言（should_speak/urgency），取 urgency ≥ 5 的前 2 位发言
- **每次发言**：1-3 句话，简洁有力
- **流式推送**：`message_start` → 多次 `message_chunk` → `free_discussion`（逐句推送）
- **共识追踪**：每 3 轮一次共识/分歧检查，实时更新
- **无人发言时**：主持人追问或推进讨论

### 3.4 第三阶段：主持人总结

- **内容**：综合所有嘉宾观点，列出共识与分歧，给出建议
- **字数**：约 200-400 字
- **纯自然语言**：禁止 JSON 或结构化格式
- **结束事件**：`moderator_summary` → `session_end` (含 consensus/divergence) → `done`

### 3.5 讨论流程

```
用户输入话题
    │
    ├── 方式A: AI 生成专家阵容 → 用户勾选确认 → 创建会话
    └── 方式B: 手动选择 3-6 位预设嘉宾 → 创建会话
        │
        ▼
  建立 SSE 连接 (GET /api/discussion/{id}/stream)
        │
        ▼
  ╔ 阶段1: 主持人开场 ╗ → SSE: moderator_opening
        │
        ▼
  ╔ 阶段2: 自主讨论 (30轮) ╗
  ║  每轮:                 ║
  ║  ① 专家并发决策        ║ → SSE: expert_status
  ║  ② urgency前2发言      ║ → SSE: message_start → chunk × N → free_discussion
  ║  ③ 每3轮共识检查       ║ → SSE: consensus_update
  ║  ④ 无人发言→主持人追问  ║ → SSE: moderator_connect
  ╚══════════════════════╝
        │
        ▼
  ╔ 阶段3: 主持人总结 ╗ → SSE: moderator_summary → session_end → done
```

---

## 4. 技术架构

### 4.1 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **前端** | React 18 + TypeScript | SPA 单页应用 |
| **前端构建** | Vite | 快速开发与构建 |
| **UI 样式** | Tailwind CSS | 原子化 CSS，快速构建中文 UI |
| **状态管理** | React Context + useReducer | 轻量级状态管理 |
| **后端** | Python 3.11+ / FastAPI | 异步 Web 框架，原生支持 SSE |
| **数据库** | SQLite | 轻量级、零配置、文件型数据库 |
| **ORM** | SQLAlchemy (async) | Python 异步 ORM |
| **LLM API** | Anthropic Messages API / OpenAI API | 生成嘉宾发言内容 |
| **实时通信** | Server-Sent Events (SSE) | 单向实时推送讨论内容 |
| **包管理** | npm (前端) / Poetry (后端) | 依赖管理 |

### 4.2 前后端分离架构

```
┌─────────────────────┐         ┌─────────────────────────────┐
│   Frontend           │         │   Backend                    │
│   (React + Vite)     │  HTTP   │   (FastAPI + Python)         │
│                      │◄───────►│                              │
│   localhost:5173     │  SSE    │   localhost:8000             │
│                      │◄────────│                              │
│                      │         │   ┌───────────────────────┐  │
│                      │         │   │  LLM Service          │  │
│                      │         │   │  (Anthropic/OpenAI)   │  │
│                      │         │   └───────────────────────┘  │
│                      │         │   ┌───────────────────────┐  │
│                      │         │   │  SQLite DB            │  │
│                      │         │   └───────────────────────┘  │
└─────────────────────┘         └─────────────────────────────┘
```

### 4.3 SSE 实时推送机制

- 后端在生成讨论内容时，每一段发言完成后立即通过 SSE 推送到前端
- 前端使用 `EventSource` API 或 `fetch` 流式读取
- SSE 事件格式：

```json
{
  "event": "guest_statement | free_discussion | moderator_opening | moderator_summary | phase_end | session_end | error",
  "data": {
    "session_id": "uuid",
    "phase": "opening | statements | free_discussion | summary",
    "round": 1,
    "speaker_id": "tech_architect",
    "speaker_name": "技术架构师",
    "content": "发言内容...",
    "timestamp": "2026-06-26T12:00:00Z"
  }
}
```

### 4.4 数据库 schema 概要

```sql
-- 讨论会话
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,    -- UUID
    topic       TEXT NOT NULL,       -- 讨论话题
    guest_ids   TEXT NOT NULL,       -- JSON: ["eff_expert","prod_mgr","tech_arch"]
    status      TEXT DEFAULT 'active', -- active | completed | error
    created_at  TEXT NOT NULL,
    completed_at TEXT
);

-- 发言记录
CREATE TABLE messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    phase       TEXT NOT NULL,       -- opening | statements | free_discussion | summary
    round       INTEGER DEFAULT 1,
    speaker_id  TEXT NOT NULL,       -- moderator | eff_expert | prod_mgr | ...
    speaker_name TEXT NOT NULL,
    content     TEXT NOT NULL,
    sequence    INTEGER NOT NULL,    -- 全局序号
    created_at  TEXT NOT NULL
);
```

---

## 5. API 接口规格

### 5.1 基础信息

- **Base URL**：`http://localhost:8000/api/v1`
- **Content-Type**：`application/json`
- **字符编码**：UTF-8

### 5.2 接口列表

#### 5.2.1 获取嘉宾列表

```
GET /api/v1/guests
```

**请求参数**：无

**响应示例**：
```json
{
  "code": 0,
  "data": [
    {
      "id": "eff_expert",
      "name": "效率专家",
      "avatar": "⚡",
      "description": "专注于流程优化、时间管理和资源利用效率",
      "personality": "追求极致效率，相信正确的方法论可以解决大多数问题"
    },
    {
      "id": "prod_mgr",
      "name": "产品经理",
      "avatar": "🎯",
      "description": "关注用户需求、市场契合度和产品价值主张",
      "personality": "始终从用户视角出发，数据驱动决策"
    },
    {
      "id": "tech_arch",
      "name": "技术架构师",
      "avatar": "🏗️",
      "description": "从系统设计、可扩展性、技术可行性角度切入",
      "personality": "兼顾工程严谨性与创新精神，关注技术债务"
    },
    {
      "id": "biz_analyst",
      "name": "商业分析师",
      "avatar": "📊",
      "description": "以ROI、市场规模、竞争优势为核心分析框架",
      "personality": "一切决策回归商业本质，用数字说话"
    },
    {
      "id": "ux_designer",
      "name": "用户体验设计师",
      "avatar": "🎨",
      "description": "以可用性、交互逻辑和用户心理模型为出发点",
      "personality": "坚信好的设计是让用户感知不到设计的存在"
    },
    {
      "id": "crit_thinker",
      "name": "批判性思考者",
      "avatar": "🔍",
      "description": "挑战假设、挖掘逻辑漏洞、找出潜在风险",
      "personality": "魔鬼代言人，对所有看似正确的结论保持警惕"
    }
  ]
}
```

---

#### 5.2.2 创建讨论会话

```
POST /api/v1/sessions
```

**请求体**：
```json
{
  "topic": "远程办公是否应该成为互联网公司的默认工作模式？",
  "guest_ids": ["eff_expert", "tech_arch", "crit_thinker"]
}
```

**请求校验**：
- `topic`：必填，1-200 个字符
- `guest_ids`：必填，数组，长度必须等于 3，元素必须为有效嘉宾 ID，不能重复

**响应示例**：
```json
{
  "code": 0,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "topic": "远程办公是否应该成为互联网公司的默认工作模式？",
    "guests": [
      {"id": "eff_expert", "name": "效率专家", "avatar": "⚡"},
      {"id": "tech_arch", "name": "技术架构师", "avatar": "🏗️"},
      {"id": "crit_thinker", "name": "批判性思考者", "avatar": "🔍"}
    ],
    "status": "active",
    "created_at": "2026-06-26T12:00:00Z"
  }
}
```

---

#### 5.2.3 获取 SSE 讨论流

```
GET /api/v1/sessions/{session_id}/stream
```

**说明**：
- 这是一个 SSE (Server-Sent Events) 端点
- 返回 `text/event-stream` 内容类型
- 连接建立后，后端按讨论流程逐阶段推送内容
- 每个阶段结束后推送该阶段的 `messages` 数据
- 整个讨论完成后推送 `[DONE]` 标识

**SSE 事件类型定义**：

| event 名称 | data 结构 | 触发时机 |
|-----------|----------|---------|
| `connected` | `{"session_id": "...", "message": "讨论即将开始..."}` | SSE 连接建立 |
| `phase_start` | `{"phase": "opening", "round": 0}` | 每个阶段开始 |
| `moderator_opening` | `{"phase": "opening", "speaker_id": "moderator", "speaker_name": "主持人", "content": "..."}` | 主持人开场输出 |
| `guest_statement` | `{"phase": "statements", "round": 1, "speaker_id": "...", "speaker_name": "...", "content": "..."}` | 每位嘉宾立场陈述 |
| `free_discussion` | `{"phase": "free_discussion", "round": 2, "speaker_id": "...", "speaker_name": "...", "content": "..."}` | 自由讨论每轮发言 |
| `moderator_summary` | `{"phase": "summary", "speaker_id": "moderator", "speaker_name": "主持人", "content": "..."}` | 主持人总结 |
| `phase_end` | `{"phase": "statements", "messages": [...]}` | 每个阶段结束，带回该阶段全部消息 |
| `session_end` | `{"session_id": "...", "topic": "...", "duration_seconds": 45.2}` | 全部讨论结束 |
| `error` | `{"code": "...", "message": "..."}` | 发生错误 |

**SSE 流示例**（原始格式）：
```
event: connected
data: {"session_id":"550e8400-...","message":"讨论即将开始..."}

event: phase_start
data: {"phase":"opening","round":0}

event: moderator_opening
data: {"phase":"opening","speaker_id":"moderator","speaker_name":"主持人","content":"各位嘉宾大家好，今天我们讨论的话题是..."}

event: phase_start
data: {"phase":"statements","round":1}

event: guest_statement
data: {"phase":"statements","round":1,"speaker_id":"eff_expert","speaker_name":"效率专家","content":"从效率的角度来看..."}

event: guest_statement
data: {"phase":"statements","round":1,"speaker_id":"tech_arch","speaker_name":"技术架构师","content":"作为技术架构师，我认为..."}

event: guest_statement
data: {"phase":"statements","round":1,"speaker_id":"crit_thinker","speaker_name":"批判性思考者","content":"我需要质疑一下前两位的观点..."}

event: phase_end
data: {"phase":"statements"}

event: phase_start
data: {"phase":"free_discussion","round":2}

event: free_discussion
data: {"phase":"free_discussion","round":2,"speaker_id":"eff_expert","speaker_name":"效率专家","content":"回应批判性思考者的质疑..."}

; ... 更多 free_discussion 事件 ...

event: phase_end
data: {"phase":"free_discussion"}

event: phase_start
data: {"phase":"summary","round":0}

event: moderator_summary
data: {"phase":"summary","speaker_id":"moderator","speaker_name":"主持人","content":"经过今天的深入讨论..."}

event: session_end
data: {"session_id":"550e8400-...","topic":"远程办公...","duration_seconds":48.3}

event: done
data: [DONE]
```

---

#### 5.2.4 获取讨论历史列表

```
GET /api/v1/sessions?page=1&page_size=20
```

**请求参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码，从 1 开始 |
| page_size | integer | 否 | 20 | 每页条数，最大 50 |

**响应示例**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "550e8400-...",
        "topic": "远程办公是否应该成为互联网公司的默认工作模式？",
        "guests": [
          {"id": "eff_expert", "name": "效率专家", "avatar": "⚡"},
          {"id": "tech_arch", "name": "技术架构师", "avatar": "🏗️"},
          {"id": "crit_thinker", "name": "批判性思考者", "avatar": "🔍"}
        ],
        "status": "completed",
        "message_count": 14,
        "created_at": "2026-06-26T12:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

---

#### 5.2.5 获取单场讨论详情

```
GET /api/v1/sessions/{session_id}
```

**响应示例**：
```json
{
  "code": 0,
  "data": {
    "id": "550e8400-...",
    "topic": "远程办公是否应该成为互联网公司的默认工作模式？",
    "guests": [
      {"id": "eff_expert", "name": "效率专家", "avatar": "⚡"},
      {"id": "tech_arch", "name": "技术架构师", "avatar": "🏗️"},
      {"id": "crit_thinker", "name": "批判性思考者", "avatar": "🔍"}
    ],
    "status": "completed",
    "messages": [
      {
        "id": "msg-001",
        "phase": "opening",
        "round": 0,
        "speaker_id": "moderator",
        "speaker_name": "主持人",
        "content": "各位嘉宾大家好...",
        "sequence": 1,
        "created_at": "2026-06-26T12:00:01Z"
      }
    ],
    "created_at": "2026-06-26T12:00:00Z",
    "completed_at": "2026-06-26T12:00:48Z"
  }
}
```

---

#### 5.2.6 删除讨论记录

```
DELETE /api/v1/sessions/{session_id}
```

**响应示例**：
```json
{
  "code": 0,
  "data": null,
  "message": "删除成功"
}
```

---

### 5.3 错误码定义

| HTTP 状态码 | code | 说明 |
|------------|------|------|
| 400 | `VALIDATION_ERROR` | 请求参数校验失败 |
| 404 | `SESSION_NOT_FOUND` | 会话不存在 |
| 409 | `SESSION_IN_PROGRESS` | 会话正在进行，无法操作 |
| 500 | `LLM_API_ERROR` | LLM API 调用失败 |
| 500 | `INTERNAL_ERROR` | 服务器内部错误 |

**错误响应格式**：
```json
{
  "code": "VALIDATION_ERROR",
  "message": "guest_ids 长度必须为 3",
  "detail": {
    "field": "guest_ids",
    "expected": 3,
    "actual": 2
  }
}
```

---

## 6. 前端页面设计

### 6.1 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 首页 - 新建讨论 | 输入话题、选择嘉宾、开始讨论 |
| `/roundtable/:id` | 讨论直播间 | SSE 实时接收并展示讨论内容 |
| `/history` | 历史记录 | 分页展示历史讨论列表 |
| `/history/:id` | 讨论回放 | 静态回放已完成讨论的全部内容 |

### 6.2 首页 UI 结构

```
┌────────────────────────────────────────────────┐
│         🤖 AI 圆桌讨论                           │
│         多视角思想碰撞，探索问题的本质                │
├────────────────────────────────────────────────┤
│                                                │
│   💬 讨论话题                                    │
│  ┌────────────────────────────────────────┐    │
│  │ 输入你想探讨的话题...                      │    │
│  └────────────────────────────────────────┘    │
│                                                │
│   👥 选择嘉宾 (请选择 3 位)                        │
│  ┌────────┐ ┌────────┐ ┌────────┐              │
│  │ ⚡     │ │ 🎯     │ │ 🏗️     │              │
│  │ 效率专家 │ │ 产品经理 │ │ 技术架构 │              │
│  │ ☑️     │ │ ☑️     │ │ ☐     │              │
│  └────────┘ └────────┘ └────────┘              │
│  ┌────────┐ ┌────────┐ ┌────────┐              │
│  │ 📊     │ │ 🎨     │ │ 🔍     │              │
│  │ 商业分析 │ │ UX设计师│ │ 批判思考 │              │
│  │ ☑️     │ │ ☐     │ │ ☐     │              │
│  └────────┘ └────────┘ └────────┘              │
│                                                │
│  ┌──────────────────────────────────────┐      │
│  │         🚀 开始讨论                    │      │
│  └──────────────────────────────────────┘      │
└────────────────────────────────────────────────┘
```

### 6.3 讨论直播间 UI 结构

```
┌────────────────────────────────────────────────┐
│  💬 远程办公是否应该成为...           ⚡🏗️🔍       │
├────────────────────────────────────────────────┤
│                                                │
│  ┌── 第一阶段：主持人开场 ──────────────────┐    │
│  │                                         │    │
│  │  🎤 主持人                              │    │
│  │  ┌─────────────────────────────────┐   │    │
│  │  │ 各位嘉宾大家好，今天我们讨论的话题  │   │    │
│  │  │ 是"远程办公是否应该成为互联网公司  │   │    │
│  │  │ 的默认工作模式？"...              │   │    │
│  │  └─────────────────────────────────┘   │    │
│  └─────────────────────────────────────────┘    │
│                                                │
│  ┌── 第二阶段：嘉宾立场陈述 ─────────────────┐    │
│  │                                         │    │
│  │  ⚡ 效率专家                             │    │
│  │  ┌─────────────────────────────────┐   │    │
│  │  │ 从效率的角度来看，远程办公允许员  │   │    │
│  │  │ 工灵活安排时间，减少通勤成本...   │   │    │
│  │  └─────────────────────────────────┘   │    │
│  │                                         │    │
│  │  🏗️ 技术架构师                         │    │
│  │  ┌─────────────────────────────────┐   │    │
│  │  │ 作为技术架构师，我认为远程协作工  │   │    │
│  │  │ 具链的成熟度是关键考量...        │   │    │
│  │  └─────────────────────────────────┘   │    │
│  └─────────────────────────────────────────┘    │
│                                                │
│  ; ... 后续阶段逐步出现 ...                       │
│                                                │
├────────────────────────────────────────────────┤
│  🔴 进行中 · 第三阶段 · 自由讨论                  │
└────────────────────────────────────────────────┘
```

---

## 7. 开发阶段规划

| 阶段 | 内容 | 预计文件 |
|------|------|---------|
| **Phase 1** | 后端项目初始化 + 数据库模型 + 嘉宾数据 seed | `backend/` |
| **Phase 2** | 后端 API 实现 (REST + SSE) | `backend/api/` |
| **Phase 3** | LLM 集成层 (System Prompt + 流式调用) | `backend/services/` |
| **Phase 4** | 前端项目初始化 + 路由 + 首页 UI | `frontend/` |
| **Phase 5** | 讨论直播间 SSE 消费 + 实时渲染 | `frontend/pages/` |
| **Phase 6** | 历史记录 + 讨论回放 | `frontend/pages/` |
| **Phase 7** | 调试优化 + 错误处理 | 全项目 |

---

## 8. 非功能性需求

- **响应延迟**：用户提交话题后 3 秒内开始收到第一段 SSE 内容
- **并发支持**：至少支持 10 场讨论同时进行
- **错误恢复**：LLM API 失败时向前端推送 `error` 事件，不丢失已完成内容
- **中文优先**：所有 UI 文案、嘉宾发言、提示词均为中文

---

> 📌 本文档为 AI Roundtable 项目的唯一需求规格来源。后续设计文档、开发任务、测试用例均以此为准。
