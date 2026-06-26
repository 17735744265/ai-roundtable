# 核心 Prompt 记录

> 本文档记录了使用 Claude Code 开发 AI 圆桌讨论项目时，每个阶段引导 AI 开发的原始 Prompt。
> 工具：Claude Code + DeepSeek V4 Pro

---

## 1. SDD 阶段 — 需求规格定义

**Prompt #1：创建需求规格文档**

```
我要开发一个"AI圆桌讨论"Web应用。请先帮我创建一份需求规格文档 SPEC.md，包含：
1. 项目概述：用户可以输入话题，选择AI嘉宾，AI嘉宾围绕话题进行多轮讨论
2. 6位预设嘉宾，各有不同的专业背景和性格
3. 讨论流程：主持人开场→每位嘉宾轮流发言→自由讨论→主持人总结
4. 技术约束：前后端分离、SSE实时推送、SQLite数据库、中文UI
5. 必须包含API接口规格定义
```

**说明**：这是项目的第一条 Prompt，目的是让 AI 先输出结构化需求文档，作为后续所有开发的"唯一真相源"。通过限定技术约束和讨论流程，避免 AI 在后续阶段自由发挥偏离方向。

---

**Prompt #2：API 契约设计**

```
根据 SPEC.md，帮我设计后端API接口，创建 docs/API_DESIGN.md，包括：
1. GET /api/experts — 获取预设嘉宾列表
2. POST /api/discussion/generate-guests — 动态生成嘉宾阵容（传入topic和expert_count）
3. POST /api/discussion/start — 创建讨论（传入topic、host、experts数组）
4. GET /api/discussion/{id}/stream — SSE流式输出讨论内容
5. GET /api/discussions — 获取历史讨论列表（支持分页和状态筛选）
6. DELETE /api/discussions/{id} — 删除讨论
每个接口要写明请求参数、响应格式、错误码和SSE事件类型
```

**说明**：有了 SPEC.md 后，下一步是让 AI 把需求翻译成精确的 API 契约。关键是在 Prompt 里把 6 个端点全部列出来，而不是让 AI 自己猜——这样 AI 的工作从"设计"变成"实现"，减少幻觉空间。

---

## 2. DDD 阶段 — 视觉驱动开发

**Prompt #3：后端项目结构与状态机**

```
帮我用 LangGraph 实现讨论流程的状态机：
1. 状态：INIT → HOST_INTRO → EXPERT_SPEAKING → FREE_DISCUSSION → HOST_SUMMARY → END
2. HOST_INTRO：主持人根据话题生成开场白
3. EXPERT_SPEAKING：按顺序让每位嘉宾发言，每位嘉宾有独立的系统prompt
4. FREE_DISCUSSION：嘉宾之间可以回应彼此观点，进行2-3轮自由讨论
5. HOST_SUMMARY：主持人总结各方观点并提炼共识与分歧
6. 使用 langchain-openai 的 ChatOpenAI，接入 DeepSeek API
7. 每个状态转换时输出对应的 SSE 事件字符串
```

**说明**：这条 Prompt 的核心是把 LangGraph 状态机的 6 个节点和状态转换规则一次性说清楚。AI 不需要"猜"讨论流程是什么，因为 Prompt 里已经定义了完整状态图。同时指定了 LLM 接入方式（ChatOpenAI + DeepSeek），避免 AI 选了不合适的库。

---

**Prompt #4：前端演播厅 UI**

```
帮我用 React + TypeScript + Tailwind CSS 实现讨论演播厅页面：
1. 三栏布局：左侧专家状态小窗 | 中间Transcript消息流 | 右侧实时共识与分歧
2. 深色演播厅主题（slate-950背景）
3. 专家状态小窗：4种状态指示灯（待机/准备/就绪/发言中），发言时有呼吸灯动画
4. Transcript区域：消息气泡按时间排列，每条显示发言人姓名+头衔+内容，不同专家用不同颜色左边框
5. 右侧共识/分歧面板：绿色=共识，橙色=分歧，实时更新
6. 使用 EventSource 连接后端 SSE 接口
7. 顶部有 ON AIR 脉冲指示灯
8. 响应式：小屏隐藏侧边栏只显示Transcript
```

**说明**：这条 Prompt 的要点是把视觉要求写得极其具体——颜色、动画、布局、响应式断点全部写明。DDD 的核心就是用"视觉描述"驱动组件拆分，而不是让 AI 自己设计 UI。把 Tailwind 的 class 名都给了，AI 只需要组装。

---

## 3. TDD 阶段 — 测试驱动

**Prompt #5：编写核心逻辑测试**

```
帮我为核心业务逻辑编写完整的 pytest 测试：
1. test_guest_generation.py：测试动态嘉宾生成的 Prompt 构建（话题注入、JSON格式要求、颜色调色板）、LLM返回JSON的解析（有效/无效/Markdown包裹）、Pydantic Schema校验
2. test_speech_scheduling.py：测试专家发言决策 Prompt、urgency 排序算法、JSON解析容错、Transcript格式化
3. test_consensus.py：测试共识/分歧检测 Prompt、解析逻辑、跨轮累积
4. test_api.py：E2E测试完整API流程（嘉宾列表/创建讨论/SSE流/历史列表/删除/多session隔离）
5. 使用 pytest-asyncio + httpx ASGITransport，不依赖真实 HTTP
6. 总共至少 50 个测试用例
```

**说明**：TDD 阶段的 Prompt 要把"测什么"列成清单，而不是说"帮我写测试"。每个测试文件覆盖哪些类、哪些方法、哪些边界条件都写清楚了。AI 的工作是从"设计测试"变成"填充测试实现"，确保覆盖面完整。

---

## 4. E2E 阶段 — 联调与集成

**Prompt #6：联调修复与集成验证**

```
帮我做一次完整的联调检查：
1. 后端启动 uvicorn app.main:app --reload --port 8000
2. 前端启动 npm run dev --port 5173
3. 检查前后端接口是否对齐（请求参数、响应格式、SSE事件类型）
4. 修复所有发现的问题
5. 确保完整流程能跑通：
   - 首页展示进行中的讨论列表
   - 输入话题 → 生成嘉宾阵容 → 确认 → 开始讨论
   - 演播厅页面实时显示主持人开场→嘉宾发言→自由讨论→总结
   - 专家状态小窗实时更新
   - 共识/分歧面板实时更新
   - 讨论结束后可以查看详情
6. 运行全部测试 pytest -q 确保通过
```

**说明**：E2E 阶段的 Prompt 是"验收清单"式的，把完整用户旅程一步步列出来。AI 逐条检查，发现问题就修。这个 Prompt 的关键不是让 AI "写代码"，而是让 AI "验证系统"——角色从开发者切换到测试员。

---

## 总结

| 阶段 | Prompt 数量 | 核心策略 |
|------|------------|---------|
| SDD | 2 条 | 先定义需求规格和 API 契约，让 AI 在精确约束下工作 |
| DDD | 2 条 | 用视觉描述驱动前端组件，用状态图驱动后端状态机 |
| TDD | 1 条 | 列出测试清单，AI 填充实现 |
| E2E | 1 条 | 验收清单式 Prompt，AI 切换到测试员角色 |

**关键经验**：给 Claude Code 的 Prompt 越具体越好。不要让 AI 做"设计决策"，而是把决策做完后让 AI 做"实现"。这就是工程化 AI 开发的核心——人定方向，AI 做执行。
