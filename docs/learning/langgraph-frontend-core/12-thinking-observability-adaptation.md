# 12. Thinking 可视化适配（LangGraph）

## 目标

回答 4 个问题：

1. LangGraph 能否直接返回“思考内容”？
2. 有哪些官方事件/字段可用于“思考感”展示？
3. 有哪些限制与风险？
4. 我们项目应该如何适配？

---

## 一、先给结论

1. LangGraph 官方保证的是**流式事件与状态可观测**，不是“必然返回模型私有思考链路”。
2. 可稳定拿到的是：`messages / updates / tasks / checkpoints / debug / custom`。
3. “思考感”应通过**执行进度 + 中间事件 + 工具轨迹**来构建，而不是依赖模型私有 CoT。

---

## 二、官方能力（可用）

参考：

- Streaming 文档：`https://docs.langchain.com/oss/python/langgraph/streaming`
- Use threads 文档：`https://docs.langchain.com/langsmith/use-threads`
- Run stream OpenAPI：`https://docs.langchain.com/langsmith/agent-server-api/thread-runs/create-run-stream-output`

### 1) 流式模式（stream_mode）

- `messages`：LLM token + metadata
- `updates`：状态增量
- `values`：完整状态
- `tasks`：任务执行轨迹
- `checkpoints`：检查点
- `debug`：调试细节
- `custom`：业务自定义流（最适合产品化“思考进度”）

### 2) 线程与历史

- `threads.get_state`：当前状态快照（含 `values.messages`）
- `threads.get_history`：历史状态序列（checkpoint 演进）

### 3) Run 入参里的关键字段（OpenAPI）

- `assistant_id`
- `context`
- `config`
- `stream_mode`
- `stream_subgraphs`
- `stream_resumable`

---

## 三、限制与风险（必须知道）

1. **不保证 provider 私有 reasoning 可见**
- LangGraph 文档没有承诺“输出完整模型思维链”。
- 不同模型厂商对 reasoning 字段支持差异很大，且常受安全策略约束。

2. **不要把私有 CoT 当成产品依赖**
- 建议只展示：token、工具步骤、节点进度、checkpoint、debug 摘要。

3. **debug 信息可能很大**
- 需要分页、折叠、按需显示，避免前端卡顿。

4. **合规风险**
- “思考面板”可能包含敏感上下文，生产环境建议做脱敏或按角色可见。

---

## 四、本项目当前可用字段（已实现链路）

### 后端透传

- 文件：`fastapi_src/api/routes.py`
- 路由：`GET /api/chat/stream`
- 行为：原样透传 chunk `event + data`，并补 `done/error`

### SSE 标准化

- 文件：`fastapi_src/services/sse_service.py`
- 格式：`event: <name>\ndata: <json>\n\n`

### 前端事件消费

- 文件：`frontend_src/src/lib/sseClient.ts`
- 已监听：
  - `messages`
  - `messages/partial`
  - `messages/metadata`
  - `updates`
  - `tasks`
  - `checkpoints`
  - `debug`
  - `values`
  - `metadata`
  - `__interrupt__`
  - `done`
  - `error`

### 前端分类（Observer）

- 文件：`frontend_src/src/pages/ObserverPage.tsx`
- 目前分类：
  - `messages*` -> `ai_stream`
  - `updates/tasks/checkpoints/debug/values` -> `state_progress`
  - `tool_calls` -> `tool_request`
  - `type==tool || tool_call_id` -> `tool_result`
  - `__interrupt__` 或 payload 中任意层级出现 `__interrupt__/interrupt/interrupts` -> `run_terminal + human_review_required`

### HITL 恢复规则（当前实现）

- 会话恢复时（`loadSessionContext`）：
  - 先从 `state` 深度提取 interrupt payload；若存在则直接进入 `human_review_required`
  - 若无 interrupt，再按 run_logs 推断终态（`error -> run_error`，`done/success -> run_done`）
- 流式消费时：
  - 一旦捕获 interrupt，会锁定 stage 为 `human_review_required`，避免后续普通流事件把状态覆盖回 `model_streaming`
  - `done` 到达时若仍处于 interrupt，则保持 HITL 状态并等待 `resume`

---

## 五、适配方案（推荐）

### 方案 A（推荐，稳定）

“Thinking 面板 = Progress 面板”

- 上半区：`messages*`（token 流）
- 中间区：`updates/tasks/checkpoints`（执行步骤）
- 下半区：`debug` 折叠展示（按需展开）

优点：不依赖私有 CoT，跨模型稳定。

### 方案 B（增强）

引入 `custom` 流作为业务态“思考卡片”

- 在图节点/工具中用 stream writer 发：
  - `phase`
  - `progress`
  - `current_tool`
  - `reason_summary`（可控摘要）

优点：产品观感最好，字段可控、可脱敏。

---

## 六、建议的 API 字段契约（前端展示用）

最小展示字段：

- `event`
- `ts`
- `node`（来自 metadata）
- `summary`（前端摘要）
- `raw`（折叠原始 payload）

如需“思考摘要”字段：

- `thinking_summary`（只允许业务可公开摘要，不存私有 CoT）

---

## 七、复刻到其他项目的步骤

1. 保持 SSE 透传 `event/data`，不自定义第二套协议。
2. 前端统一做事件分层：`ai_stream / tool / progress / terminal`。
3. 优先接 `messages+updates+tasks+checkpoints+debug`。
4. 若要更像“思考面板”，再引入 `custom` 结构化进度。
5. 对 debug/thinking 数据加折叠、分页、权限控制。
