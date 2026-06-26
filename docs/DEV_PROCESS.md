# 开发流程与工程化思考

> 作者：陈雅 | 工具：Claude Code + DeepSeek V4 Pro | 耗时：约 36 小时

---

## 一、开发流程概览

整个项目按 SDD → DDD → TDD → E2E 四个阶段推进，每个阶段有明确的输入和输出。

**SDD 阶段**（约 4h）：先不写代码，让 Claude Code 输出 SPEC.md 需求规格和 API_DESIGN.md 接口契约。这一步最重要——需求定清楚了，后面 AI 才不会乱跑。产出 8 个 Pydantic Schema + 6 个 TypeScript 接口，编译时就锁死了前后端的数据格式。

**DDD 阶段**（约 12h）：分两路并行。后端用 LangGraph 搭建 4 节点状态机（init → host_intro → autonomous_discussion → host_summary），前端用 React + Tailwind 搭建演播厅三栏布局。这阶段代码量最大，Claude Code 的效率也最高——我描述完状态转换规则和 UI 布局后，它一次性生成了 15 个后端文件和 15 个前端文件。

**TDD 阶段**（约 8h）：给核心逻辑写测试。5 个测试文件、52 个用例，覆盖了 Prompt 构建、JSON 解析容错、发言调度算法、共识检测和完整 API 流程。用 pytest-asyncio + httpx ASGITransport 实现异步测试，不需要真实的 LLM API 调用。

**E2E 阶段**（约 6h）：前后端联调，修了若干 SSE 事件对齐、跨域配置、数据库级联删除等问题。最后全量测试通过，确认完整用户旅程跑通。

---

## 二、典型问题与解决路径

### 问题 1：LangGraph 状态机中数据库会话传递

**现象**：在 LangGraph 节点函数里直接传 SQLAlchemy AsyncSession 到 state，导致序列化报错——LangGraph 的 state 要求所有字段可序列化。

**排查**：读 LangGraph 文档发现 state 会通过 pickle 序列化传递给下一个节点，数据库连接对象不能序列化。

**解决**：把 db session 从 state 中移除，改为通过 LangGraph 的 `config.configurable` 传递。state 只保留纯数据（消息列表、SSE 事件字符串），数据库操作在节点函数内部通过 config 获取 session 完成。

### 问题 2：SSE 事件类型前后端不对齐

**现象**：后端推送了 `expert_status` 事件，但前端 `useSSE.ts` 里没注册这个事件类型的监听器，导致专家状态小窗不更新。

**排查**：在浏览器 DevTools 的 Network 面板查看 SSE 流，发现后端推了 12 种事件类型，但前端只注册了 8 种。

**解决**：在 `types/index.ts` 中统一定义 `SSEEventType` 联合类型（12 种），`useSSE.ts` 循环注册所有类型的监听器，确保后端新增事件类型时前端不会遗漏。同时在 `ENGINEERING_PHASES.md` 里把 SSE 事件契约作为"前后端唯一接口规范"固化下来。

### 问题 3：动态嘉宾生成的 JSON 解析容错

**现象**：LLM 返回的嘉宾阵容有时包裹在 Markdown 代码块里（```json ... ```），有时前后有多余文本，直接 `JSON.parse` 会报错。

**排查**：测试了 20 次 API 调用，发现约 30% 的返回不是纯 JSON。

**解决**：写了一个多层解析策略——先尝试直接 parse，失败后用正则提取 ```json``` 包裹的内容，再失败则扫描整个响应找第一个 `[` 和最后一个 `]` 之间的内容。同时在 Prompt 里明确要求"只输出 JSON，不要任何解释文字"。测试覆盖了 5 种异常输入格式。

---

## 三、对"工程化 AI 开发"的理解

传统开发是"人写所有代码"。AI 辅助开发变成了"人定方向 + AI 做执行"。但这不意味着人更轻松了——反而对"说清楚需求"的要求更高了。

用 Claude Code 开发这个项目的核心体会是：**Prompt 的质量直接决定代码的质量**。模糊的 Prompt 出来的代码需要大量返工，精确的 Prompt 一次就能跑通。

具体来说：

1. **先定义契约，再写实现**——SDD 阶段花 4 小时写的 SPEC.md 和 API 设计文档，节省了后面至少 20 小时的返工。因为 AI 有了精确的"施工图纸"。

2. **用文档当上下文锚点**——5 份 docs 文档不只是给人看的，更是给 Claude Code 看的。每次让它改代码前，先让它读相关文档，这样它不会偏离方向。

3. **测试是最好的验收标准**——52 个测试用例不是为了"凑覆盖率"，而是让 AI 改完代码后立刻知道改对没改对。每次 `pytest -q` 全绿就是验收通过。

4. **Git commit 是安全网**——每完成一个阶段就 commit，万一 AI 把代码改崩了，随时可以 `git reset` 回到上一个好的状态。

总结一句话：**工程化 AI 开发的本质不是让 AI 替代人写代码，而是让人用工程化的方法管理 AI 的输出质量。**
