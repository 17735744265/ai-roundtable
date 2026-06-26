# AI 圆桌讨论 — 前端架构与技术实现

---

## 1. 技术栈

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **框架** | React | 19.2.7 | UI 组件框架 |
| **语言** | TypeScript | 6.0.2 | 类型安全 |
| **构建** | Vite | 8.1.0 | 开发服务器 + 生产构建 |
| **路由** | react-router-dom | 7.18.0 | 客户端 SPA 路由 |
| **样式** | Tailwind CSS | 4.3.1 | 原子化 CSS 框架 |
| **Lint** | oxlint | 1.69.0 | 代码检查 |
| **状态管理** | React Context + useReducer | — | 轻量级全局状态（无第三方库） |
| **实时通信** | EventSource (SSE) | — | 浏览器原生 API，无额外依赖 |

---

## 2. 项目目录结构

```
frontend/
├── index.html                       # SPA 入口 HTML，lang="zh-CN"
├── package.json                     # 依赖与脚本
├── vite.config.ts                   # Vite 配置（React + Tailwind + API 代理）
├── tsconfig.json                    # TypeScript 项目引用
├── tsconfig.app.json                # TS 编译配置（es2023, bundler mode）
└── src/
    ├── main.tsx                     # ReactDOM.createRoot 入口
    ├── App.tsx                      # 路由配置 + 全局导航栏
    ├── index.css                    # Tailwind 入口 + 全局样式
    │
    ├── types/
    │   └── index.ts                 # 18 个 TS 类型/接口定义
    │
    ├── api/                         # ── API 通信层 ──
    │   ├── client.ts                # fetch 封装 + 错误处理 + base URL
    │   ├── guests.ts                # GET /api/experts
    │   └── sessions.ts              # POST /discussion/start, GET /discussions 等
    │
    ├── store/
    │   └── roundtable-context.tsx   # Context + useReducer 讨论直播状态
    │
    ├── hooks/
    │   └── useSSE.ts               # EventSource 封装 + 事件解析 + 断线重连
    │
    ├── pages/                       # ── 页面组件 ──
    │   ├── HomePage.tsx             # 首页：话题输入 + 嘉宾选择
    │   ├── RoundtablePage.tsx       # 讨论直播间（Provider 挂载）
    │   ├── HistoryPage.tsx          # 历史记录列表（分页）
    │   └── HistoryDetailPage.tsx    # 讨论回放（静态渲染）
    │
    └── components/                  # ── UI 组件 ──
        ├── home/
        │   ├── TopicInput.tsx       # 话题输入框（200 字限制）
        │   └── GuestSelector.tsx    # 嘉宾卡片网格（6 选 3）
        ├── roundtable/
        │   ├── RoundtableRoom.tsx   # 直播间主容器：SSE → Reducer → UI
        │   ├── PhaseSection.tsx     # 阶段分组容器
        │   ├── MessageBubble.tsx    # 发言气泡（按 speaker 着色）
        │   └── ConnectionStatus.tsx # SSE 连接指示器
        └── common/                  # 通用组件（预留给 Layout 等）
```

---

## 3. 分层架构

```
┌─────────────────────────────────────────────┐
│                 Pages (页面)                  │
│   组合 Components，调用 API，持有局部 state     │
├─────────────────────────────────────────────┤
│              Components (组件)                │
│   纯 UI 渲染，接收 props，触发回调              │
├─────────────────────────────────────────────┤
│            Store / Hooks (状态)               │
│   Context + useReducer / useSSE              │
├─────────────────────────────────────────────┤
│               API (通信层)                    │
│   client.ts → fetch 封装 → 后端 HTTP/SSE      │
├─────────────────────────────────────────────┤
│               Types (类型层)                  │
│   18 个 TS 接口，贯穿全部层级                    │
└─────────────────────────────────────────────┘
```

**数据流方向**（单向）：

```
User Action → Page → API → Backend
                          ↓
SSE Event ← Backend
    ↓
useSSE Hook → processSSEEvent → Reducer → State → Components → UI
```

---

## 4. 类型系统

所有类型定义在 [`src/types/index.ts`](../frontend/src/types/index.ts)，共 18 个接口/类型。

### 4.1 核心实体类型

```typescript
// 嘉宾
interface Guest {
  id: string;          // "eff_expert"
  name: string;        // "效率专家"
  avatar: string;      // "⚡"
  description: string; // 一句话定位
  personality: string; // 思维特征
}

// 消息
interface Message {
  id: string;           // UUID
  session_id: string;   // 所属讨论
  phase: 'opening' | 'statements' | 'free_discussion' | 'summary';
  round: number;        // 0=开场/总结, 1=陈述, 2-3=讨论
  speaker_id: string;   // "moderator" | "eff_expert" | ...
  speaker_name: string; // "主持人" | "效率专家" | ...
  content: string;      // 发言正文
  sequence: number;     // 全局序号
  created_at: string;   // ISO 8601
}
```

### 4.2 会话类型

```typescript
interface SessionBrief {          // 列表项（不含 messages）
  id, topic, guests: GuestBrief[],
  status: 'active' | 'completed' | 'error',
  message_count: number,
  created_at: string
}

interface SessionDetail {         // 详情（含全部 messages）
  id, topic, guests: GuestBrief[],
  status, messages: Message[],
  created_at, completed_at
}
```

### 4.3 SSE 事件类型

```typescript
type SSEEventType =
  | 'connected' | 'phase_start'
  | 'moderator_opening' | 'guest_statement'
  | 'free_discussion' | 'moderator_summary'
  | 'phase_end' | 'session_end' | 'done' | 'error';

interface SSEEvent {
  type: SSEEventType;
  data: SSEData;  // 包含所有可能的字段（session_id, phase, content...）
}
```

### 4.4 前端状态类型

```typescript
type DiscussionPhase =
  | 'connecting' | 'opening' | 'statements'
  | 'free_discussion' | 'summary' | 'completed' | 'error';

interface DiscussionState {
  sessionId: string;
  topic: string;
  phase: DiscussionPhase;
  currentRound: number;
  messages: Message[];
  isConnected: boolean;
  error: string | null;
  durationSeconds: number;
}
```

### 4.5 API 响应包装

```typescript
interface ApiResponse<T> { code: number; message: string; data: T; }
interface PaginatedData<T> { items: T[]; total: number; page: number; page_size: number; }
```

---

## 5. API 通信层

### 5.1 基础封装

**文件**：[`src/api/client.ts`](../frontend/src/api/client.ts)

```typescript
const BASE_URL = 'http://localhost:8000/api';  // 或 VITE_API_BASE_URL 环境变量

// 3 个核心函数
apiGet<T>(path)    → GET  → 解包 json.data
apiPost<T>(path, body) → POST → 解包 json.data
apiDelete(path)    → DELETE

// SSE URL 构建
sseUrl(path) → `${BASE_URL}${path}`
```

**设计要点**：
- 基于原生 `fetch` API，零依赖
- 自动从 `{ code, message, data }` 中解包 `data` 字段
- 非 2xx 响应抛 `ApiError(status, code, message)`
- 支持 `VITE_API_BASE_URL` 环境变量覆盖 base URL

### 5.2 业务 API

```typescript
// guests.ts
fetchGuests() → GET /api/experts → Guest[]

// sessions.ts
createSession({ topic, guest_ids }) → POST /api/discussion/start → SessionDetail
fetchSessions(page, pageSize)       → GET /api/discussions → PaginatedData<SessionBrief>
fetchSession(id)                    → GET /api/discussions/{id} → SessionDetail
deleteSession(id)                   → DELETE /api/discussions/{id}
```

---

## 6. 状态管理

### 6.1 Context + useReducer 架构

```
  RoundtableProvider (Context)
  ┌─────────────────────────────────────┐
  │                                     │
  │  useReducer(reducer, initState)     │
  │       │                             │
  │       ├── state: DiscussionState    │
  │       └── dispatch: (Action) => void │
  │                                     │
  │  processSSEEvent(event)             │
  │    → dispatch appropriate action    │
  │                                     │
  └────────────┬────────────────────────┘
               │ Context value
               ▼
  useRoundtable() ← 任何子组件可访问
```

### 6.2 Action 类型（7 种）

| Action | 触发源 | state 变更 |
|--------|--------|-----------|
| `CONNECTED` | SSE `connected` 事件 | 写入 sessionId, topic |
| `PHASE_START` | SSE `phase_start` 事件 | 切换 phase, currentRound |
| `ADD_MESSAGE` | 4 种发言 SSE 事件 | messages[] 追加一条 |
| `PHASE_END` | SSE `phase_end` 事件 | 无状态变更（占位） |
| `SESSION_END` | SSE `session_end` 事件 | phase → `completed` |
| `ERROR` | SSE `error` 事件 | phase → `error`，写入 error |
| `DISCONNECTED` | SSE 连接断开 | isConnected → false |

### 6.3 SSE 事件 → Reducer 映射

```typescript
function processSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'connected'           → dispatch({ type: 'CONNECTED', ... })
    case 'phase_start'         → dispatch({ type: 'PHASE_START', ... })
    case 'moderator_opening'   → dispatch({ type: 'ADD_MESSAGE', ... })
    case 'guest_statement'     → dispatch({ type: 'ADD_MESSAGE', ... })
    case 'free_discussion'     → dispatch({ type: 'ADD_MESSAGE', ... })
    case 'moderator_summary'   → dispatch({ type: 'ADD_MESSAGE', ... })
    case 'phase_end'           → dispatch({ type: 'PHASE_END' })
    case 'session_end'         → dispatch({ type: 'SESSION_END', ... })
    case 'error'               → dispatch({ type: 'ERROR', ... })
    case 'done'                → 不 dispatch（仅标记连接结束）
  }
}
```

---

## 7. SSE Hook 设计

**文件**：[`src/hooks/useSSE.ts`](../frontend/src/hooks/useSSE.ts)

### 7.1 架构

```
useSSE(sessionId, { onEvent, enabled })
  │
  ├── connectionState: 'connecting' | 'open' | 'closed' | 'error' | 'done'
  ├── retryCount: number
  ├── connect()      → 建立 EventSource
  ├── disconnect()   → 关闭连接
  └── reconnect()    → 手动重连
```

### 7.2 生命周期

```
connect()
  │
  ├─ new EventSource(`/api/discussion/{id}/stream`)
  │
  ├─ es.onopen        → connectionState='open', retryCount=0
  │
  ├─ es.addEventListener(type)
  │    └─ 对 10 种 event type 注册监听
  │    └─ 解析 JSON → onEvent({ type, data })
  │    └─ type==='done' → connectionRef='done'
  │
  └─ es.onerror
       ├─ connectionRef='done' → 不重试（正常结束）
       ├─ retryCount < 3       → 指数退避重连 (1s→2s→4s)
       └─ retryCount >= 3      → 显示手动重试按钮
```

### 7.3 断线重连策略

| 状态 | 行为 |
|------|------|
| **流正常结束**（收到 `done` 事件） | `onerror` 检测到 `connectionRef === 'done'`，不重试 |
| **异常断开**（网络问题） | 指数退避：1s → 2s → 4s，最多 3 次 |
| **重试耗尽**（3 次失败） | 显示"重试连接"按钮，用户手动触发 |
| **409 Conflict**（session 已结束） | `onerror` 触发但不再重试（`done` 标记） |

### 7.4 清理机制

```typescript
useEffect(() => {
  if (enabled && sessionId) connect();
  return () => disconnect();  // 组件卸载时关闭 EventSource + 清除 timer
}, [sessionId, enabled]);
```

---

## 8. 路由设计

| 路径 | 页面组件 | 数据源 | 说明 |
|------|---------|--------|------|
| `/` | `HomePage` | `GET /api/experts` | 话题输入 + 嘉宾选择（6 选 3） |
| `/roundtable/:id` | `RoundtablePage` → `RoundtableRoom` | SSE Stream | 实时讨论直播间 |
| `/history` | `HistoryPage` | `GET /api/discussions` | 分页历史列表 |
| `/history/:id` | `HistoryDetailPage` | `GET /api/discussions/:id` | 静态回放已完成讨论 |

### 导航栏

所有页面共享 `Navbar` 组件（`App.tsx`），始终显示"新建讨论"和"历史记录"链接。

---

## 9. 页面数据流

### 9.1 首页（HomePage）

```
1. useEffect → fetchGuests() → setGuests(6位嘉宾)
2. 用户输入话题 + 选择 3 位嘉宾
3. 点击"开始讨论" → createSession() → 获得 session.id
4. navigate(`/roundtable/${session.id}`)
```

**状态**：3 个 `useState` — `guests`、`selectedIds`、`topic`  
**校验**：`topic.trim().length > 0 && selectedIds.length === 3`

### 9.2 讨论直播间（RoundtablePage → RoundtableRoom）

```
1. RoundtablePage 从 URL 提取 :id
2. 包裹 <RoundtableProvider>（创建 Context + Reducer）
3. RoundtableRoom 调用 useSSE(sessionId, { onEvent: processSSEEvent })
4. useSSE 建立 EventSource → 接收 SSE 事件 → processSSEEvent → dispatch
5. Reducer 更新 DiscussionState → 触发 UI 重渲染
```

**关键**：`useSSE` 的 `onEvent` 回调中调用 `processSSEEvent`，这是一个稳定的 `useCallback`（依赖 `state.sessionId` 和 `state.messages.length`）。

### 9.3 历史记录（HistoryPage）

```
1. useEffect(page) → fetchSessions(page) → setSessions + setTotal
2. 渲染分页列表 + 手动翻页
3. 删除：window.confirm → deleteSession(id) → 重新加载当前页
```

**状态**：`sessions`、`total`、`page`、`loading`、`error`

### 9.4 讨论回放（HistoryDetailPage）

```
1. useEffect(id) → fetchSession(id) → setSession(SessionDetail)
2. 按 phase 分组消息：opening / statements / free_discussion / summary
3. 重用 PhaseSection + MessageBubble 组件静态渲染
```

---

## 10. 组件树

```
App
├── Navbar
└── <Routes>
    │
    ├── HomePage
    │   ├── TopicInput          (受控 textarea, 200字限制)
    │   └── GuestSelector       (3×2 网格, 每格一个嘉宾卡片)
    │
    ├── RoundtablePage
    │   └── RoundtableProvider  (Context)
    │       └── RoundtableRoom
    │           ├── ConnectionStatus  (绿/黄/红 指示灯)
    │           ├── PhaseSection × 4  (按阶段分组)
    │           │   └── MessageBubble × N  (按 speaker 着色)
    │           └── 空态/完成态/错误态
    │
    ├── HistoryPage
    │   └── SessionBrief 列表 + 分页
    │
    └── HistoryDetailPage
        └── PhaseSection × 4   (复用)
            └── MessageBubble × N  (复用)
```

### 组件职责

| 组件 | 类型 | 职责 |
|------|------|------|
| `TopicInput` | 受控组件 | 渲染 textarea + 字数统计，通过 `onChange` 回传值 |
| `GuestSelector` | 展示组件 | 渲染 6 张嘉宾卡片，高亮已选，阻止超选 |
| `RoundtableRoom` | 容器组件 | 组装 useSSE + useRoundtable，派发消息到子组件 |
| `PhaseSection` | 展示组件 | 按阶段标题分组，包裹 MessageBubble 列表 |
| `MessageBubble` | 展示组件 | 单条发言气泡：7 种 speaker 配色 + 展开/收起 |
| `ConnectionStatus` | 展示组件 | 连接状态指示灯 + 阶段文字 + 重试按钮 |

---

## 11. 样式系统

### 11.1 Tailwind CSS 配置

通过 `@tailwindcss/vite` 插件集成，零配置。全局样式入口在 `src/index.css`：

```css
@import "tailwindcss";
/* 全局 body 样式 + 自定义滚动条 */
```

### 11.2 设计语言

| 要素 | Token | 说明 |
|------|-------|------|
| **背景** | `slate-900` → `slate-800` 渐变 | 深色主题，减少视觉疲劳 |
| **文字** | `white` / `slate-300` / `slate-400` / `slate-500` | 四级灰度层次 |
| **强调色** | `blue-500` → `purple-600` 渐变 | 主按钮（"开始讨论"） |
| **成功** | `emerald-400/500` | 连接中动画 / 完成标记 |
| **错误** | `red-400/500` | 错误提示 / 异常标记 |
| **嘉宾色** | 7 种独立配色 | 每位 speaker 有独特的 `color` + `bg` + `border` 组合 |
| **圆角** | `rounded-2xl` / `rounded-xl` | 统一使用大圆角，现代感 |
| **毛玻璃** | `bg-slate-900/80 backdrop-blur-md` | 导航栏 |

### 11.3 嘉宾配色映射

```typescript
const speakerStyles = {
  moderator:    { color: 'text-amber-300',  bg: 'bg-amber-500/10  border-amber-500/20'  },
  eff_expert:   { color: 'text-yellow-300', bg: 'bg-yellow-500/10 border-yellow-500/20' },
  prod_mgr:     { color: 'text-blue-300',   bg: 'bg-blue-500/10   border-blue-500/20'   },
  tech_arch:    { color: 'text-purple-300', bg: 'bg-purple-500/10 border-purple-500/20' },
  biz_analyst:  { color: 'text-green-300',  bg: 'bg-green-500/10  border-green-500/20'  },
  ux_designer:  { color: 'text-pink-300',   bg: 'bg-pink-500/10   border-pink-500/20'   },
  crit_thinker: { color: 'text-red-300',    bg: 'bg-red-500/10    border-red-500/20'    },
};
```

每位发言者在讨论中有唯一的视觉标识，便于快速区分。

---

## 12. Vite 构建配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [
    react(),        // @vitejs/plugin-react
    tailwindcss(),  // @tailwindcss/vite
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 开发时代理到后端
        changeOrigin: true,
      },
    },
  },
});
```

**TypeScript 编译配置**：`es2023` target、`bundler` module resolution、JSX `react-jsx` 模式。

---

## 13. 生产构建产物

```
dist/
├── index.html                   0.56 kB (gzip 0.40 kB)
├── assets/
│   ├── index-ClROGyCQ.css      29.34 kB (gzip 5.73 kB)
│   └── index-CA-nPeKY.js      252.09 kB (gzip 79.95 kB)
```

总计约 80 kB gzip，单页面加载，无代码分割（当前规模无需 lazy loading）。

---

## 14. 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| **状态管理** | Context + useReducer | 状态规模小（仅讨论直播间需要全局状态），无需 Redux/Zustand |
| **SSE 消费** | 原生 EventSource | 浏览器内置，自动重连，零依赖 |
| **HTTP 请求** | 原生 fetch | 接口简单，无需 axios 的拦截器等功能 |
| **路由** | react-router-dom v7 | 4 个路由，client-side navigation 足够 |
| **样式** | Tailwind CSS v4 | 原子化 CSS，快速构建 UI，无需独立 CSS 文件 |
| **TS 严格模式** | `noUnusedLocals/Params: true` | 编译时即发现未使用变量 |
| **组件复用** | `PhaseSection` + `MessageBubble` | 直播页和回放页共用同一套渲染组件 |
| **隔离状态** | `RoundtableProvider` 仅包裹直播页 | 避免讨论状态泄漏到其他页面 |
| **重连策略** | `connectionRef` 区分正常结束 vs 异常断开 | 解决 SSE 流完成后 EventSource 自动重连的 409 问题 |

---

> 📌 本文档与 [SPEC.md](../SPEC.md)、[API_DESIGN.md](API_DESIGN.md)、[BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) 配套。本文档侧重前端内部实现细节与架构决策。
