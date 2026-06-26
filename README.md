# 🤖 AI 圆桌讨论 (AI Roundtable)

基于大语言模型的沉浸式圆桌讨论平台。用户输入话题，AI 动态生成专家阵容，专家**自主决定发言时机**，实时进行多视角深度辩论。

---

## 快速开始

### 环境要求

| 工具 | 版本 |
|------|------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |

### 1. 克隆项目

```bash
git clone <repo-url>
cd ai-roundtable
```

### 2. 后端配置

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env .env  # 已有 .env 则跳过
# 编辑 .env 填入 LLM API Key
```

### 3. 初始化数据库

```bash
# 仅创建表
python scripts/init_db.py

# 创建表 + 插入 5 条样例数据
python scripts/init_db.py --seed
```

### 4. 启动后端

```bash
uvicorn app.main:app --reload
# → http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 环境变量

在 `backend/.env` 中配置（仅后端读取，**绝不暴露到浏览器**）：

```bash
# ── LLM Provider: "deepseek" | "anthropic" | "openai" ──
LLM_PROVIDER=deepseek

# DeepSeek (推荐，性价比最高)
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Anthropic (备选)
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-4-6

# OpenAI (备选)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# ── 讨论配置 ──
FREE_DISCUSSION_ROUNDS=2       # 自主讨论轮数 (2-4)
CORS_ORIGINS=http://localhost:5173
DEBUG=false
```

---

## 技术选型

### 前端

| 技术 | 用途 | 选型理由 |
|------|------|---------|
| **React 19** | UI 框架 | 最成熟的前端生态，TypeScript 支持完善 |
| **TypeScript 6** | 类型安全 | 端到端类型校验，编译时发现错误 |
| **Vite 8** | 构建工具 | 毫秒级 HMR，原生 ESM |
| **Tailwind CSS 4** | 样式 | 原子化 CSS，快速迭代 UI |
| **react-router-dom 7** | 路由 | SPA 路由标准 |
| **EventSource** | SSE 消费 | 浏览器原生，零依赖，自动重连 |

### 后端

| 技术 | 用途 | 选型理由 |
|------|------|---------|
| **FastAPI** | Web 框架 | 原生 async/await，自动 OpenAPI 文档 |
| **LangGraph 1.2** | AI 编排 | 状态图管理讨论流程，支持 astream 流式输出 |
| **langchain-openai** | LLM 接入 | 统一接口调用 DeepSeek/OpenAI |
| **SQLAlchemy 2.0** | ORM | async session，aiosqlite 驱动 |
| **SQLite** | 数据库 | 零配置部署，文件型，WAL 模式支持并发 |
| **httpx** | HTTP 客户端 | 异步调用 Anthropic/OpenAI API |

### 测试

| 技术 | 用途 |
|------|------|
| **pytest** | 测试框架 |
| **pytest-asyncio** | 异步测试支持 |
| **httpx (ASGITransport)** | 无真实 HTTP 的 API 测试 |

---

## 主要 API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/experts` | 获取 6 位预设嘉宾 |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/discussion/generate-guests` | LLM 动态生成主持+专家阵容 |
| `POST` | `/api/discussion/start` | 创建新讨论会话 |
| `GET` | `/api/discussion/{id}/stream` | SSE 实时讨论流 (12 种事件) |
| `GET` | `/api/discussions` | 历史讨论列表 (分页+筛选) |
| `GET` | `/api/discussions/{id}` | 讨论详情 (含全部消息) |
| `DELETE` | `/api/discussions/{id}` | 删除讨论记录 |

完整 API 文档见 [`docs/API_DESIGN.md`](docs/API_DESIGN.md) 或启动后端后访问 `http://localhost:8000/docs` (自动生成的 Swagger UI)。

---

## 项目文档

| 文档 | 说明 |
|------|------|
| [SPEC.md](SPEC.md) | 需求规格文档 |
| [docs/PRD.md](docs/PRD.md) | 产品需求文档 (Mermaid 用户故事/状态图) |
| [docs/API_DESIGN.md](docs/API_DESIGN.md) | API 接口设计 (6 端点 + 12 SSE 事件) |
| [docs/ER_DIAGRAM.md](docs/ER_DIAGRAM.md) | 数据库 ER 图 + 数据字典 (Mermaid) |
| [docs/BACKEND_ARCHITECTURE.md](docs/BACKEND_ARCHITECTURE.md) | 后端架构与分层设计 |
| [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) | 前端架构与组件树 |
| [docs/ENGINEERING_PHASES.md](docs/ENGINEERING_PHASES.md) | SDD→DDD→TDD 工程范式拆解 |

---

## 已完成能力

### 核心功能
- [x] LLM 动态生成主持+专家阵容（姓名/Title/立场/专属颜色）
- [x] 专家自主决定发言时机（并发 LLM 决策，非机械轮流）
- [x] 1-2 句简洁发言，真实辩论感
- [x] SSE 实时推送 12 种事件类型
- [x] 演播厅三栏沉浸式布局（专家状态/Transcript/共识追踪）
- [x] ON AIR 指示灯 + 呼吸灯 + 扫描线演播厅动画
- [x] 实时共识与分歧提炼（每约 3 条消息触发）
- [x] 自然语言主持人总结（无 JSON 暴露）
- [x] 进行中讨论列表 + 加入观察已有讨论
- [x] 历史记录分页 + 静态回放
- [x] 响应式布局（3 断点：<1024 / 1024-1536 / >1536）

### 工程质量
- [x] API Key 仅后端环境变量，前端不接触
- [x] 多会话 SSE 流隔离（session_id FK + Context 实例隔离）
- [x] 各区域独立滚动容器（Transcript/侧边栏不互相影响）
- [x] 52 个单元测试 + E2E 测试
- [x] 数据库初始化脚本 + 5 条高质量种子数据
- [x] 7 份完整技术文档
- [x] Git 分阶段提交历史

### 开发范式
- [x] **SDD**: SPEC.md → Pydantic/TS 类型 → API 契约 → ER 图
- [x] **DDD**: 演播厅视觉语言 → 组件树 → 状态流转 → 动画系统
- [x] **TDD**: 52 tests (14 guest-gen + 17 scheduling + 10 consensus + 11 API)

---

## 后续改进方向

### 短期 (P0-P1)
- [ ] 讨论录制导出 (Markdown/PDF)
- [ ] 用户自定义编辑生成的嘉宾信息
- [ ] 多语言支持 (英文 UI + 英文讨论)
- [ ] 讨论分享链接生成
- [ ] 预设嘉宾模板保存

### 中期 (P2)
- [ ] TTS 语音合成，将发言转为语音流
- [ ] AI 生成真人风格嘉宾头像 (替代 emoji)
- [ ] 讨论热度/嘉宾参与度可视化图表
- [ ] Docker 一键部署

### 长期 (P3)
- [ ] OAuth 用户系统 + 个人讨论历史
- [ ] WebSocket 替代 SSE，支持真人用户介入讨论
- [ ] 讨论质量评分 + 用户反馈

---

## 运行测试

```bash
cd backend

# 运行全部测试
python -m pytest tests/ -v

# 仅运行核心逻辑测试 (不需要 LLM)
python -m pytest tests/test_guest_generation.py tests/test_speech_scheduling.py tests/test_consensus.py -v
```

---

## 项目结构

```
ai-roundtable/
├── README.md                         # 本文件
├── SPEC.md                           # 需求规格
├── .gitignore
├── backend/
│   ├── .env                          # 环境变量 (不提交)
│   ├── requirements.txt              # Python 依赖
│   ├── scripts/
│   │   └── init_db.py                # 数据库初始化 + 种子数据
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── config.py                 # 配置管理
│   │   ├── database.py               # SQLAlchemy 引擎
│   │   ├── exceptions.py             # 异常体系
│   │   ├── models/                   # ORM 数据模型
│   │   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── routers/                  # API 路由层
│   │   └── services/                 # 业务逻辑层
│   │       ├── llm_service.py        # LLM 统一调用
│   │       ├── prompt_manager.py     # Prompt 模板库
│   │       ├── discussion_orchestrator.py  # LangGraph 编排引擎
│   │       └── session_service.py    # CRUD 服务
│   └── tests/                        # 测试套件
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx                   # 路由 + 导航
│       ├── types/index.ts            # TS 类型定义
│       ├── api/                      # API 通信层
│       ├── store/                    # 状态管理
│       ├── hooks/                    # SSE Hook
│       ├── pages/                    # 4 个页面
│       └── components/               # UI 组件
└── docs/                             # 技术文档
    ├── PRD.md                        # 产品需求 (Mermaid 图)
    ├── API_DESIGN.md                 # API 接口设计
    ├── ER_DIAGRAM.md                 # ER 图 + 数据字典
    ├── BACKEND_ARCHITECTURE.md       # 后端架构
    ├── FRONTEND_ARCHITECTURE.md      # 前端架构
    └── ENGINEERING_PHASES.md         # 工程范式拆解
```

---

## License

MIT
