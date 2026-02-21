# Step 3：Streaming 事件流观测（官方扩展版）

## 0. 学习目标

这一章解决 3 件事：

1. 你能读懂 `runs.stream` 返回的事件流。
2. 你能说清 `wait-run`（结果）和 `stream-run`（过程）的边界。
3. 你能区分 agent 里的模型输出、工具输出、MCP 工具输出，以及“计划类数据（ToDo）”应该放在哪里。

官方文档：

- https://docs.langchain.com/langsmith/streaming
- https://docs.langchain.com/oss/python/langgraph/streaming

## 1. 先建立 Streaming 心智模型

- `wait-run`：拿最终结果，适合后端同步调用。
- `stream-run`：拿执行过程，适合前端实时展示与调试。
- `thread_id` 存在：有状态流（结果会沉淀到 thread state/history）。
- `thread_id=None`：无状态流（只看本次，不写持久状态）。

## 2. 官方 stream_mode 对照（你要记住）

| mode | 作用 | 你在学习里怎么用 |
|---|---|---|
| `updates` | 每步状态增量 | 看每个节点更新了什么 |
| `values` | 每步完整状态 | 对比全量状态变化 |
| `messages` / `messages-tuple` | LLM token + metadata | 做实时打字机输出、按节点过滤 |
| `debug` | 详细调试信息 | 排错首选 |
| `custom` | 业务自定义流 | 发进度、计划、结构化标记 |
| `events` | 全事件流（迁移场景常用） | 做全量观察与兼容迁移 |

补充：可多模式同时传，例如 `stream_mode=["updates","custom"]`。

## 3. 本项目最小实操（你已完成，但要能复述）

### 3.1 Stateful stream（有状态）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请给我两条学习建议" \
  --stream-mode updates,messages,tasks,checkpoints,debug
```

### 3.2 Wait 对照

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请给我两条学习建议"
```

### 3.3 State 回读

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py state --thread-id <THREAD_ID>
```

## 4. 如何区分输出类型（你问的重点）

> 结论先说：在 agent 视角里，MCP 输出本质上也是工具输出；要区分“本地工具 vs MCP 工具”，需要用工具命名约定和 metadata 标记。

### 4.1 模型输出（LLM output）

常见判断信号：

- `messages` 流里出现 token chunk（`messages`/`messages-tuple`）
- 最终消息中出现 `type=ai`（在 wait/state 中可见）

### 4.2 工具输出（Tool output）

常见判断信号：

- `tasks` / `updates` 里出现工具节点执行痕迹
- AI 消息包含 `tool_calls`
- 后续出现 tool message（工具执行结果）

### 4.3 MCP 输出（MCP tool output）

关键点：**MCP 在运行时会被注入为 tools，事件层面仍按“工具调用”表现。**

在本项目里可通过工具名区分来源：

- 本地 tools：`word_count` / `utc_now` / `to_upper`
- 本地 MCP（示例）：`add` / `multiply` / `square` / `reverse_text` / `text_length`

建议：

- 给工具命名加前缀（如 `mcp_math_add`）或在 metadata 打来源标记。

### 4.4 ToDo 计划类输出（计划/进度）

官方做法建议放在 `custom` 流里，而不是混在普通自然语言消息中。

推荐结构：

```json
{"type":"plan","phase":"research","progress":40,"todo":["...","..."]}
```

这样前端可稳定解析，不需要从自然语言里猜。

## 5. 项目内可复现的“工具 vs MCP”观察命令

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请调用 add 计算 2+3，并调用 to_upper 输出 hello" \
  --config-json '{"recursion_limit":60,"configurable":{"enable_local_tools":true,"enable_local_mcp":true,"mcp_servers":["local_math"]}}' \
  --stream-mode updates,messages,tasks,checkpoints,debug
```

观察点：

- `tasks` / `updates` 中是否出现工具调用轨迹
- 输出中能否看到 `add`（MCP）与 `to_upper`（本地工具）行为差异

## 6. 常见问题与排错

1. 看不到事件
- 检查 `--stream-mode` 是否传空或拼错

2. `stream` 有事件但 `state` 没沉淀
- 检查是否传了 `thread_id`（无状态不会沉淀）

3. `join_stream` 少了前半段输出
- 官方限制：join 不会补发你加入前的历史流

4. 想输出“计划进度”但事件难解析
- 用 `custom` 模式发结构化 JSON

## 7. 本章验收标准

- 你能解释至少 4 种 stream mode 的用途。
- 你能用实际流事件指出一次模型输出和一次工具输出。
- 你能说明“为什么 MCP 输出在事件层面看起来仍是工具输出”。
- 你能给出 ToDo/计划类数据的结构化流方案（`custom`）。

## 8. 对应自动化测试（Streaming S1）

- 测试文件：`tests/test_streaming_stage_s1.py`
- 覆盖链路：创建 thread -> stream-run 事件观测 -> wait-run 结果对照 -> state 沉淀校验 -> 清理

执行方式（显示详细日志）：

```bash
uv run --with pytest pytest tests/test_streaming_stage_s1.py -vv -s
```

## 9. 深入学习入口

- Run 执行全景：`docs/learning/langgraph-sdk/03-runs-api-playbook.md`
- Runtime + MCP：`docs/learning/langgraph-sdk/06-runtime-dynamic-config-playbook.md`
- Runtime Context：`docs/learning/langgraph-sdk/08-langgraph-runtime-context-runnables-playbook.md`

## 10. 官方“可机读信号”判定清单（前端最关键）

基于官方 `streaming` 文档，前端建议按“信号优先”而不是“文案猜测”来判断阶段：

1. 用户输入
- 来源：你自己的请求体（`input.messages`）
- 作用：作为本轮会话起点，立即渲染

2. LLM 思考 / 生成 token
- 推荐信号：`messages`（或 `messages-tuple`）模式
- 典型形态：token chunk + metadata（包含 `langgraph_node`）

3. 工具调用请求
- 推荐信号：
  - token 流中的 `tool_call_chunk`
  - 完整消息中的 `tool_calls`

4. 工具执行结果
- 推荐信号：`updates` 中 `tools` 节点的 `ToolMessage`
- 作用：标记某个工具已完成执行并返回结果

5. AI 最终输出
- 推荐信号：`updates` 中 `model` 节点最终 `AIMessage`
- 辅助信号：token 流结束（如 chunk 结束位）

6. 运行结束
- 服务层常见信号：流结束 / `done` 事件（你的 SSE 包装层可统一发）

## 11. DeepAgent 专项调研结论（官方）

你质疑得对：在 DeepAgent 场景里，ToDo **不是必须自定义**。

官方结论：

- DeepAgent 内置 `TodoListMiddleware`
- 会自动给 agent 提供 `write_todos` 工具
- ToDo 项通常包含状态：`pending / in_progress / completed`

同时 DeepAgent 还内置文件系统能力（由 FilesystemMiddleware / harness 提供）：

- `ls`
- `read_file`
- `write_file`
- `edit_file`
-（文档还给出 `glob` / `grep`）

因此在 DeepAgent 里：

- ToDo 计划更新通常以 `write_todos` 工具调用表现
- 写文件/读文件等步骤通常以文件工具调用表现
- 这些在事件层本质都属于“工具调用链”，区别在 tool 名称和参数

## 12. 前端对接建议（可直接落地）

建议前端维护一个轻量状态机：

1. `user_input_received`
2. `model_streaming`
3. `tool_calling`（可细分：`tool_local` / `tool_mcp` / `tool_deepagent_todo` / `tool_deepagent_fs`）
4. `tool_completed`
5. `final_answer`
6. `run_done` / `run_error`

分类规则建议：

- `tool_name == "write_todos"` -> `tool_deepagent_todo`
- `tool_name in {"ls","read_file","write_file","edit_file","glob","grep"}` -> `tool_deepagent_fs`
- `tool_name in 本地工具白名单` -> `tool_local`
- `tool_name in MCP 工具白名单` -> `tool_mcp`

> 注意：MCP 输出在事件层仍是工具输出，前端要靠“工具名分层”来区分来源。

## 13. 关于“tests 是否要按官方例子调整”

建议：要。

当前 `tests/test_streaming_stage_s1.py` 已覆盖 stream/wait/state 闭环，但若要对齐官方前端集成语义，建议新增/补强两类测试：

1. `messages` 模式测试
- 验证 token 与 metadata（如 node 信息）可被消费

2. 工具调用链测试
- 验证“工具调用请求 -> 工具结果 -> 最终 AI 输出”的可观测顺序

这两条测试已在 `tests/test_streaming_stage_s1.py` 增强实现。

继续学习请转到：

- `16-deepagent-todo-skills-files-playbook.md`
- `17-streaming-frontend-backend-standard.md`
- `18-streaming-stage-s2-subgraphs-join-custom.md`
