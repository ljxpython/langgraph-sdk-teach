# 10. Controls 字段能力与前后端调用映射

## 目标

回答 4 个核心问题：

1. `tools_profile` 是做什么的？
2. 后端当前到底支持动态切换哪些字段？
3. `model_provider` / `model_name` 各自语义是什么，是否都必要？
4. 前端点击后调用了哪些接口，前端字段与后端字段如何对应？

---

## 一、结论先说

- `model_provider`：后端 **已支持并生效**。
- `model_name`：当前前端已移除，不再作为控制字段。
- `mcp_servers`：后端 **已支持并生效**。
- `custom_tools`：当前是前端控制字段，后端 **未消费**（预留位）。

采样参数默认对齐策略（最新实现）：

- LangGraph 层默认：`temperature/top_p/max_tokens` 都是 `None`（即不强制覆盖模型默认）。
- 前端 Controls 新增“使用 LangGraph 默认采样参数”开关，默认开启。
- 开启时前端不会在 `context` 中发送这三项；关闭后才发送手动值。

tools/mcp 默认与开关语义（最新实现）：

- LangGraph 默认：`enable_local_tools=true`、`enable_local_mcp=false`。
- 前端 Controls 默认对齐：tools 开、mcp 关。
- 后端已按 `enable_local_mcp` 严格 gating，关闭时不会加载 MCP tools。

补充：历史消息能力现在采用 LangGraph 推荐路径：

- 实时增量：`runs.stream`
- 当前会话快照：`threads.get_state`
- 历史轨迹：`threads.get_history`

---

## 二、字段语义说明（含是否生效）

| 字段 | 当前语义 | 后端是否读取 | 实际生效位置 |
|---|---|---|---|
| `model_provider` | 选择模型提供方/路由（如 `glm4`/`deepseek`/`kimi`） | 是 | `graph_src/agent.py` `build_runtime_options` -> `resolve_model` |
| `model_name` | （已移除） | 否 | 当前无消费逻辑 |
| `system_prompt` | 覆盖系统提示词 | 是 | `graph_src/agent.py` `build_runtime_options` |
| `temperature` | 采样温度 | 是 | `graph_src/agent.py` `apply_model_runtime_params` |
| `top_p` | nucleus 采样 | 是 | `graph_src/agent.py` `apply_model_runtime_params` |
| `max_tokens` | 最大输出 token | 是 | `graph_src/agent.py` `apply_model_runtime_params` |
| `enable_local_tools` | 启用本地工具集 | 是 | `graph_src/agent.py` `build_agent_from_config` |
| `enable_local_mcp` | 启用 MCP 工具加载 | 是 | `graph_src/agent.py` `build_agent_from_config` |
| `mcp_servers` | 指定 MCP server 列表 | 是 | `graph_src/agent.py` `_parse_mcp_servers` + `get_mcp_tools` |
| `custom_tools` | 前端自定义工具名列表 | 否 | 当前无消费逻辑 |

---

## 三、`model_provider` 与 `model_name` 是否都需要

### 当前代码现实

- 当前 graph 运行时只用 `model_provider` 做模型路由，`model_name` 没有进入选择链。
- 目前前端已移除 `model_name`，避免误导。

### 什么时候需要 `model_name`

- 当你希望在同一 provider 下切不同具体模型（例如 openai 下 `gpt-4o-mini` / `gpt-4.1-mini`）时才需要。
- 这需要后端在 `resolve_model` 或 `llms.py` 增加 `model_name` 读取与分发逻辑。

---

## 四、前端点击 -> 后端接口调用链

### A. 通用对话工作台（Observer）

| 前端操作 | 前端入口 | 调用接口 | 后端入口 |
|---|---|---|---|
| 新建 Session | `ObserverPage.handleCreateSession` | `POST /api/thread` | `routes.create_or_get_thread` |
| 切换 Session（缺 thread 自动补建） | `ObserverPage.handleSelectSession` | `POST /api/thread` | `routes.create_or_get_thread` |
| 切换 Session（回填上下文） | `ObserverPage.loadSessionContext` | `GET /api/messages` + `GET /api/state` + `GET /api/history` + `GET /api/run-logs` | `routes.get_messages/get_state/get_history/get_run_logs` |
| 消息分页加载更早记录 | `ObserverPage.loadMoreMessagesForActiveSession` | `GET /api/messages?limit=30&offset=N` | `routes.get_messages` |
| Start Stream 提交 | `ObserverPage.handleStartStream` | `POST /api/thread` | `routes.create_or_get_thread` |
| Start Stream 提交 | `ObserverPage.handleStartStream` | `GET /api/chat/stream`（SSE） | `routes.chat_stream` |
| 刷新 assistant 列表 | `ControlPanel` 按钮 -> `loadAssistants` | `GET /api/assistants` | `routes.get_assistants` |
| 刷新 State | `StatePanel` 按钮 -> `handleRefreshState` | `GET /api/state` | `routes.get_state` |
| 刷新 Logs | `DebugPanel` 按钮 -> `handleRefreshLogs` | `GET /api/run-logs` | `routes.get_run_logs` |
| Approve Resume | `StatePanel` 按钮 -> `handleApproveResume` | `POST /api/chat/resume` | `routes.chat_resume` |

### B. Assistant 管理页（AssistantManagePage）

| 前端操作 | 前端入口 | 调用接口 | 后端入口 |
|---|---|---|---|
| 刷新 graph 下拉 | `loadGraphs` | `GET /api/graphs` | `routes.get_graphs` |
| 刷新 assistants | `loadAssistants` | `GET /api/assistants` | `routes.get_assistants` |
| 创建 assistant | `handleCreate` | `POST /api/assistants` | `routes.create_assistant` |
| 更新 assistant | `handleUpdate` | `PATCH /api/assistants/{assistant_id}` | `routes.update_assistant` |
| 删除 assistant | `handleDelete` | `DELETE /api/assistants/{assistant_id}` | `routes.delete_assistant` |

---

## 五、Observer Controls 字段 -> 后端字段映射

### 请求装配位置

- 前端：`frontend_src/src/pages/ObserverPage.tsx` `contextPayload`。
- 传输：`context_json` 查询参数进入 `/api/chat/stream`。
- 后端：`fastapi_src/api/routes.py` `chat_stream` 解析 `context_json`。
- 归一化：`fastapi_src/services/chat_service.py` `normalize_context_and_config`。
- 运行时消费：`graph_src/agent.py` `build_runtime_options`。

| 前端字段（Observer） | 发送键 | 后端解析键 | 当前是否生效 |
|---|---|---|---|
| `system_prompt` | `system_prompt` | `context.system_prompt` | 是 |
| `temperature` | `temperature` | `context.temperature` | 是 |
| `top_p` | `top_p` | `context.top_p` | 是 |
| `max_tokens` | `max_tokens` | `context.max_tokens` | 是 |
| `model_provider` | `model_provider` | `context.model_provider` | 是 |
| `model_name` | （无） | （无） | 否 |
| `enable_local_mcp` | `enable_local_mcp` | `context.enable_local_mcp` | 是 |
| `mcp_servers` | `mcp_servers` | `context.mcp_servers` | 是 |
| `custom_tools` | `custom_tools` | `context.custom_tools` | 否（未消费） |

---

## 六、`tools_profile` 现在是什么状态

当前前端已移除 `tools_profile`，因为没有明确业务场景且后端未消费。

---

## 七、建议的下一步（最小可落地）

1. 在 `graph_src/agent.py` 增加 `tools_profile` 消费逻辑（先做 3 档：`none/default/research`）。
2. 如未来有明确需求，再在 `graph_src/agent.py` 增加 `model_name` 消费逻辑。
3. 前端持续只暴露“后端已生效”的字段，减少误导。

---

## 八、LangGraph 消息相关接口（官方语义）

1. `threads.create`：创建会话容器（thread）。
2. `runs.wait`：单次执行并返回结果消息。
3. `runs.stream`：流式返回 `messages/updates/tasks/debug` 等事件。
4. `runs.join_stream`：重连已存在 run 的流（不保证补发历史事件）。
5. `threads.get_state`：读取 thread 当前状态快照（含 `values.messages`）。
6. `threads.get_history`：读取 thread 的状态演进历史（checkpoint 序列）。

当前 FastAPI 映射：

- `/api/chat/stream` -> `runs.stream`
- `/api/state` -> `threads.get_state`
- `/api/messages` -> `threads.get_state`（提取 `values.messages` 并归一化，支持 `limit/offset`）
- `/api/history` -> `threads.get_history`

---

## 九、当前会话模块的交互逻辑

1. Session 列支持侧栏式折叠（收窄为窄列，保留操作图标）。
2. Controls 列支持侧栏式折叠（收窄为窄列，保留操作图标）。
3. Session 绑定 `assistant_id + controls` 参数；切换 session 时自动恢复这些参数。
4. 新建 Session 立即创建/复用 thread。
5. 进入 Session 会自动拉取：消息首屏 + 最新 state + history checkpoints + run logs。
6. 消息过多时按 `limit/offset` 加载更早页，避免一次性拉全量。

---

## 十、Assistant 与 Thread 的关系（LangGraph 实践）

1. Thread 是状态容器，Run 执行时需要显式传 `assistant_id`。
2. 同一个 thread 技术上可切换 assistant 运行，但实践上建议“一个会话固定一个 assistant”，避免上下文和能力边界漂移。
3. 当前实现采用会话绑定策略：每个 Session 保存自己的 `assistant_id` 与运行参数，`resume` 使用同一 assistant。
