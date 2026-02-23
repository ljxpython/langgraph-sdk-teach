# 09. AI 平台核心功能清单与调用链路（Learning MVP）

## 目标

把学习项目收敛为“最小可跑通 AI 平台”，并把前端点击到 LangGraph API 的链路全部说清楚，便于联调、排障和共创优化。

---

## 一、功能清单（按优先级）

### P0（必须先跑通）

1. 通用智能体对话闭环
- 能力：单会话输入 -> 模型输出 -> 终态结束。
- 落地：`/api/thread` + `/api/chat/stream`（或 `/api/chat/wait`）。
- 验收：一次请求可看到 `messages*` 与 `done/error`。

2. 工具调用闭环（Tool Request/Result）
- 能力：能区分工具请求与工具结果。
- 落地：前端按 `tool_calls`、`type=="tool"` 分类显示。
- 验收：Timeline 可观察 `tool_request` 与 `tool_result`。

3. HITL 审批与恢复
- 能力：命中 `__interrupt__` 后可审批并恢复执行。
- 落地：前端触发 `POST /api/chat/resume`，后端走 `runs.wait(..., command=...)`。
- 验收：出现 `__interrupt__` 后能完成一次 approve -> resume -> done/error。

4. 可观测与可排障
- 能力：每个 run 可追踪事件、状态、日志。
- 落地：`TimelinePanel` + `GET /api/state` + `GET /api/run-logs`。
- 验收：能从 UI 定位 `thread_id`、关键事件、错误。

5. 最小多模态输入（建议版）
- 能力：先支持“文本 + 图片 URL/附件元数据透传”，不做重型视觉流水线。
- 落地：在 `input.messages[].content` 增加多段内容结构，后端透传给 `runs.wait/stream`。
- 验收：多段 content 能被链路接收并在 state/log 中可回查。

### P1（P0 稳定后）

1. 多智能体/子任务委托（task/subgraph）
2. 长短期记忆分层（thread state + 检索记忆）
3. 评测回归（固定用例、成功率、延迟、成本）
4. 安全护栏（工具白名单、输入输出约束）
5. 流式恢复增强（`join_stream`）

---

## 二、前端“每次点击”到后端接口链路

### A. 会发起网络请求的交互

1. `Start Stream`（提交表单）
- 入口：`frontend_src/src/pages/ObserverPage.tsx` `handleStartStream`
- 前端调用：
  - `createOrGetThread(user_id)` -> `POST /api/thread`（幂等兜底）
  - `openStream(params)` -> `GET /api/chat/stream`（SSE）
- 后端路由：`fastapi_src/api/routes.py`
  - `create_or_get_thread`
  - `chat_stream`

2. `新建 Session`
- 入口：`frontend_src/src/pages/ObserverPage.tsx` `handleCreateSession`
- 前端调用：`createOrGetThread(user_id)` -> `POST /api/thread`
- 后端路由：`fastapi_src/api/routes.py:create_or_get_thread`

3. `切换 Session`（缺 thread 时自动补建）
- 入口：`frontend_src/src/pages/ObserverPage.tsx` `handleSelectSession`
- 前端调用：`createOrGetThread(user_id)` -> `POST /api/thread`（仅当本地 `thread_id` 为空）
- 后端路由：`fastapi_src/api/routes.py:create_or_get_thread`

4. `进入 Session 自动回填上下文`
- 入口：`frontend_src/src/pages/ObserverPage.tsx` `loadSessionContext`
- 前端并行调用：
  - `GET /api/messages?limit=30&offset=0`（最新消息页）
  - `GET /api/state`（最新 state 快照）
  - `GET /api/history?limit=20`（checkpoint 历史）
  - `GET /api/run-logs`（调试日志）
- 目标：进入会话即看到消息、state 摘要、checkpoint 时间线、日志。

5. `消息分页（加载更早消息）`
- 入口：`frontend_src/src/pages/ObserverPage.tsx` `loadMoreMessagesForActiveSession`
- 前端调用：`GET /api/messages?limit=30&offset=<current_offset>`
- 后端行为：按 thread 最新消息做倒序窗口切片后返回。

6. `刷新 assistant/graph 列表`
- 入口：`frontend_src/src/components/ControlPanel.tsx`
- 前端调用：`getAssistants(...)` -> `GET /api/assistants`
- 后端路由：`fastapi_src/api/routes.py:get_assistants`

7. `刷新 State`
- 入口：`frontend_src/src/components/StatePanel.tsx`
- 前端调用：`getState(user_id)` -> `GET /api/state`
- 后端路由：`fastapi_src/api/routes.py:get_state`

8. `Approve Resume`
- 入口：`frontend_src/src/components/StatePanel.tsx`
- 前端调用：`resumeChat(...)` -> `POST /api/chat/resume`
- 后端路由：`fastapi_src/api/routes.py:chat_resume`
- 约束：使用当前 Session 绑定的 `assistant_id`，不再固定为某个 assistant。

9. `刷新 Logs`
- 入口：`frontend_src/src/components/DebugPanel.tsx`
- 前端调用：`getRunLogs(user_id)` -> `GET /api/run-logs`
- 后端路由：`fastapi_src/api/routes.py:get_run_logs`

### B. 不发起网络请求的交互（本地状态）

1. `Stop`：仅关闭 `EventSource`（前端本地）
2. `新建 Session`：仅更新前端 session 状态
3. `切换 Session`：仅切换本地选中会话并清空展示态
4. 参数输入/滑杆（`assistant_id/system_prompt/temperature/top_p/max_tokens`）：仅本地状态变更

> 注：`graph_id` 变更本身是本地状态，但会触发 `useEffect -> loadAssistants`，间接请求 `GET /api/assistants`。

---

## 三、FastAPI -> LangGraph SDK -> LangGraph API 映射

1. `POST /api/thread`
- Service：`ChatService.create_or_get_thread` / `_create_thread`
- SDK：`client.threads.create()`
- 对应 LangGraph API：`POST /threads`

2. `POST /api/chat/wait`
- Service：`ChatService.wait_chat`
- SDK：`client.runs.wait(thread_id, assistant_id, input=..., context=..., config=...)`
- 对应 LangGraph API：`POST /threads/{thread_id}/runs/wait`

3. `POST /api/chat/resume`
- Service：`ChatService.resume_chat`
- SDK：`client.runs.wait(thread_id, assistant_id, input=None, command=...)`
- 对应 LangGraph API：`POST /threads/{thread_id}/runs/wait`（带 `command.resume`）

4. `GET /api/chat/stream`
- Service：`routes.chat_stream`（内联组装 stream 参数）
- SDK：`client.runs.stream(thread_id, assistant_id, input=..., stream_mode=..., context=..., config=...)`
- 对应 LangGraph API：`POST /threads/{thread_id}/runs/stream`

5. `GET /api/state`
- Service：`ChatService.get_state`
- SDK：`client.threads.get_state(thread_id)`
- 对应 LangGraph API：`GET /threads/{thread_id}/state`

6. `GET /api/assistants`
- Service：`ChatService.list_assistants`
- SDK：`client.assistants.search(limit, offset, graph_id?)`
- 对应 LangGraph API：`POST /assistants/search`

7. `GET /api/run-logs`
- Service：`ChatService.get_run_logs`
- SDK：无（本地 SQLite 日志）
- 对应 LangGraph API：无

---

## 四、当前实现里的关键兼容策略

1. thread 保活与自愈
- `ensure_thread` 先 `threads.get(existing)` 验活，失败则自动新建。

2. context-only 归一化
- 若同时传 `context` 和 `config.configurable`，后端会把 configurable 合并进 context 并移除 configurable。

3. 流式终态统一
- 后端在透传官方事件外补充 `done/error`，前端终态判定更稳定。

---

## 五、我们可以一起优化的下一步（建议）

1. 把“多模态最小输入”接到现有 `Start Stream` 表单（先 URL/元数据，不加复杂上传服务）。
2. 给每条点击链路补“请求样例 + 预期响应样例 + 失败分支”。
3. 为 `join_stream` 增加可选恢复入口，并在 UI 增加“断线恢复”开关。
4. 增加一套最小回归脚本：对 P0 五项能力逐条验收并留日志证据。

---

## 六、当前前端会话与参数逻辑（已实现）

1. Sessions 列支持侧栏式折叠，收起时仅保留窄列与操作按钮。
2. 新建 Session 即创建/复用 thread；切换 Session 自动回填 state/history/messages。
3. 聊天消息按 `limit/offset` 分页加载“更早消息”。
4. Sampling 参数默认走 LangGraph 默认值（前端不发送 `temperature/top_p/max_tokens`），仅在手动关闭默认策略后发送覆盖值。
