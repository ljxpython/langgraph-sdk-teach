# 11. 平台能力复刻手册（可迁移到其他项目）

## 目标

把当前项目里已经验证通过的平台化能力沉淀成“可复刻模板”，用于在其他 LangGraph 项目快速落地。

---

## 一、推荐复刻顺序

1. 先打通线程主链路：`thread -> stream -> state -> history -> resume`
2. 再做会话层：session 绑定 assistant 与参数
3. 再做界面层：侧栏折叠、消息分页、Markdown 渲染、复制按钮
4. 最后做校验层：构建 + API 回归测试

---

## 二、会话与 Assistant 绑定策略

### 复刻原则

- 一个 Session 绑定一组运行上下文：
  - `assistant_id`
  - `model_provider`
  - sampling 参数（temperature/top_p/max_tokens）
  - tools/mcp 开关与列表
- 切换 session 时恢复这组参数。
- `resume` 必须使用当前 session 绑定的 `assistant_id`，禁止硬编码。

### 复刻收益

- 避免“切换会话后参数漂移”。
- 避免 `resume` 到错误 assistant/graph。

---

## 三、Controls 参数策略（已验证）

### 采样参数默认对齐

- LangGraph 默认：`temperature/top_p/max_tokens = None`（不覆盖模型默认）。
- 前端提供“使用 LangGraph 默认采样参数”开关（默认开）。
- 开启时不发送 sampling 字段；关闭后才发送手动值。

### tools / mcp 开关语义

- 后端默认：`enable_local_tools=true`，`enable_local_mcp=false`。
- 前端显式透传两个布尔值，避免语义歧义。
- 当 `enable_local_mcp=false` 时：
  - 前端不发送 `mcp_servers`
  - 后端不加载 MCP tools（强 gating）

---

## 四、消息与历史最佳实践

### 读取策略

- 实时输出：`runs.stream`
- 当前快照：`threads.get_state`
- 历史轨迹：`threads.get_history`

### 分页策略

- 消息接口支持 `limit/offset`
- 初次进入 session 拉首屏（例如 30 条）
- 用户点击“加载更早消息”继续分页

---

## 五、UI 复刻清单

### 平台壳层

- 左侧主导航支持折叠
- Session 列支持折叠（窄列模式）
- Controls 列支持折叠（窄列模式）

### Chat Panel

- AI/User 消息卡片化
- 支持 Markdown（GFM）渲染
- 每条消息底部提供“小图标复制按钮”
- 流式草稿区支持同样复制能力

### Session 可读性

- 会话卡显示：`assistant_id`、`thread_id`、更新时间
- 明确锁定提示：该 session 使用自己的 assistant/参数快照

---

## 六、接口映射模板（可直接复用）

- `POST /api/thread`：创建或复用 thread
- `GET /api/chat/stream`：流式对话
- `POST /api/chat/resume`：中断恢复
- `GET /api/state`：状态快照
- `GET /api/history`：checkpoint 历史
- `GET /api/messages?limit=&offset=`：消息分页
- `GET /api/run-logs`：调试日志

---

## 七、验收标准（迁移项目必做）

1. 新建 session 后立即拿到 `thread_id`
2. 切换 session 能恢复 assistant 与参数
3. `resume` 使用当前 session 的 assistant
4. `enable_local_mcp=false` 时不会加载 MCP tools
5. Markdown 渲染与复制按钮都可用
6. 消息分页可向前翻页

### 子 agent / 工具调用标准回归 Prompt

前置：`assistant_id=deepagent_demo`

- 子 agent（task）：
  - `请把“做一个前端平台改版”拆成3个子任务，并分别委托子代理执行后汇总结果。`
- 工具调用（write_todos）：
  - `请先创建一个待办清单：1) 调研 LangGraph stream_mode；2) 写出验证步骤；3) 输出风险项，然后继续执行。`
- 文件工具（write_file/edit_file）：
  - `请新建 docs/tmp_hitl_demo.md，写入“这是一次 HITL 测试”，然后把第一行改成“已通过 HITL 审批测试”。`

预期：

1. Chat 中可见 `tool_request/tool_result/state_progress`
2. 需要人工审批时出现 `__interrupt__`
3. `Approve Resume` 后进入 `done/error`

---

## 八、最小回归命令

- 前端：`npm run build`
- 后端：`uv run --with pytest pytest tests/fastapi_test -q`
- 运行时参数：`uv run --with pytest pytest tests/test_runtime_context_model_params.py -q`

---

## 九、`agent-chat-ui` 历史消息恢复实现（参考标准）

### 1) Thread 身份由 URL 参数驱动

- 使用 `threadId` query 参数作为当前会话键。
- 文件：`example/ui_demo/src/components/thread/index.tsx`、`example/ui_demo/src/providers/Stream.tsx`

### 2) useStream 直接绑定 thread 并开启历史抓取

- `useStream({ threadId, fetchStateHistory: true, ... })`
- 当 `threadId` 变化时，SDK 自动切换到该 thread 并恢复对应状态/消息。
- 文件：`example/ui_demo/src/providers/Stream.tsx`

### 3) 消息列表直接来源于 `stream.messages`

- 渲染层不额外维护一套“聊天历史缓存”，而是消费 SDK 状态。
- 文件：`example/ui_demo/src/components/thread/index.tsx`

### 4) 历史线程列表通过 `threads.search` 拉取

- `ThreadProvider.getThreads()` 调 `client.threads.search(...)`
- 依据 `assistant_id`/`graph_id` 过滤历史 thread。
- 文件：`example/ui_demo/src/providers/Thread.tsx`

### 5) 点击历史会话即切换 threadId

- `ThreadHistory` 点击后 `setThreadId(t.thread_id)`，界面恢复该线程的历史消息。
- 文件：`example/ui_demo/src/components/thread/history/index.tsx`

### 6) 新对话语义

- `setThreadId(null)` 即开始新线程语义（下一次 submit 由 SDK 创建新 thread）。
- 文件：`example/ui_demo/src/components/thread/index.tsx`

### 复刻建议

1. 优先采用“`threadId` 作为唯一会话键”而不是仅靠 `user_id`。
2. 消息恢复优先走 SDK 状态（或后端 `messages` API），避免前端本地拼接历史。
3. 保留 `threads.search` 的历史列表入口，点击即恢复。

当前仓库已按该模式落地：

- 新增 `GET /api/threads`（读取线程列表）
- 新增 `POST /api/thread/new`（显式新建线程）
- `state/messages/history/run-logs` 支持 `thread_id` 读取
- 前端 `ObserverPage` 优先按 `thread_id` 作为会话主键恢复历史
