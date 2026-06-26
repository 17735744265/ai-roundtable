# AI 圆桌讨论 — 需求规格文档

---

## 1. 项目概述

### 1.1 项目名称

**AI Roundtable** — AI 圆桌讨论平台

### 1.2 项目简介

AI Roundtable 是一个基于大语言模型的实时圆桌讨论 Web 应用。用户输入一个话题，并从 6 位预设 AI 专家中选取 3 位，系统自动模拟一场结构化的圆桌讨论：主持人开场 → 嘉宾轮流发言 → 自由辩论 → 主持人总结。讨论内容通过 Server-Sent Events (SSE) 实时推送到前端，为用户提供沉浸式的多视角思想碰撞体验。

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
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  第一阶段     │ → │  第二阶段     │ → │  第三阶段     │ → │  第四阶段     │
│  主持人开场   │    │  嘉宾轮流发言  │    │  自由讨论     │    │  主持人总结   │
│  (~200字)    │    │  每人1轮     │    │  2-3轮交叉   │    │  (~400字)    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### 3.2 第一阶段：主持人开场 (Moderator Opening)

- **触发**：用户提交话题 + 选定嘉宾后自动开始
- **内容**：主持人（系统）对话题进行背景介绍，明确讨论边界，引导嘉宾入场
- **字数**：约 150-250 字
- **SSE 事件类型**：`moderator_opening`
- **嘉宾不参与此阶段**

### 3.3 第二阶段：嘉宾轮流发言 (Position Statements)

- **顺序**：按用户选择嘉宾的先后顺序依次发言
- **内容**：每位嘉宾陈述自己对该话题的核心观点和基本立场
- **每人字数**：约 200-350 字
- **每位嘉宾发言对应一个 SSE 事件**：`guest_statement`
- **阶段结束事件**：`phase_end` (phase: "statements")

### 3.4 第三阶段：自由讨论 (Free Discussion / Cross-talk)

- **轮次**：2-3 轮自由交叉讨论
- **参与方式**：每轮由主持人指定"发言方向"（如"请 B 回应 A 的观点"），然后由 LLM 综合前文上下文生成该嘉宾的回应
- **内容特征**：嘉宾可引用、赞成、反驳、补充其他嘉宾的观点
- **每人每轮字数**：约 150-300 字
- **SSE 事件类型**：`free_discussion`
- **阶段结束事件**：`phase_end` (phase: "free_discussion")

### 3.5 第四阶段：主持人总结 (Moderator Summary)

- **内容**：综合所有嘉宾观点，提炼共识与分歧，给出行动建议或后续思考方向
- **字数**：约 300-500 字
- **SSE 事件类型**：`moderator_summary`
- **最后一个 SSE 事件**：`session_end`（包含完整讨论的数据库 ID）

### 3.6 流程图

```
用户输入话题 + 选择3位嘉宾
        │
        ▼
  创建讨论会话 (POST /api/sessions)
        │
        ▼
  建立 SSE 连接 (GET /api/sessions/:id/stream)
        │
        ▼
  ╔══════════════════════════════╗
  ║  阶段1: 主持人开场            ║ → SSE: moderator_opening
  ╚══════════════════════════════╝
        │
        ▼
  ╔══════════════════════════════╗
  ║  阶段2: 嘉宾1发言             ║ → SSE: guest_statement
  ║         嘉宾2发言             ║ → SSE: guest_statement
  ║         嘉宾3发言             ║ → SSE: guest_statement
  ╚══════════════════════════════╝ → SSE: phase_end
        │
        ▼
  ╔══════════════════════════════╗
  ║  阶段3: 自由讨论 轮次1        ║ → SSE: free_discussion × N
  ║         自由讨论 轮次2        ║ → SSE: free_discussion × N
  ║         自由讨论 轮次3        ║ → SSE: free_discussion × N
  ╚══════════════════════════════╝ → SSE: phase_end
        │
        ▼
  ╔══════════════════════════════╗
  ║  阶段4: 主持人总结            ║ → SSE: moderator_summary
  ╚══════════════════════════════╝ → SSE: session_end
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
