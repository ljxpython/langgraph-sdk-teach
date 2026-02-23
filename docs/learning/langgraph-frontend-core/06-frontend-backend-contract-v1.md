# 06. Frontend-Backend Contract v1

## 目标

冻结一份最小联调契约，确保前后端实现一致、测试可复现。

## 核心原则

1. 以 LangGraph SDK 官方语义为准：`event` / `data` / `__interrupt__`
2. 不定义二次业务协议，不重写事件语义
3. 仅允许传输层补充：`done` / `error`
4. 运行时参数统一走 `context`（`temperature/max_tokens/top_p/system_prompt`）
5. 不再从前端发送 `config.configurable`

## HTTP 接口契约

1. `POST /api/thread`
- 入参：`user_id`
- 出参：`user_id`、`thread_id`、`created`

2. `POST /api/chat/wait`
- 入参：`user_id`、`message`、可选 `assistant_id/context/config`
- 出参：`thread_id`、`result`

3. `POST /api/chat/resume`
- 入参：`user_id`、`command`、可选 `assistant_id`
- 出参：`thread_id`、`result`

4. `GET /api/chat/stream`
- 入参：`user_id`、`message`、可选 `assistant_id/stream_mode/context_json/config_json`
- 流式返回：`event` + `data`（官方透传）
- 传输终态：`event: done` / `event: error`

5. `GET /api/state`
- 入参：`user_id`
- 出参：`thread_id`、`state`

6. `GET /api/run-logs`
- 入参：`user_id`
- 出参：`user_id`、`items[]`（wait/stream/resume 日志）

7. `GET /api/assistants`
- 入参：可选 `graph_id/limit/offset`
- 出参：`items[]`，每项为 `assistant_id`、`graph_id`、`name`

## 事件消费契约（前端）

1. `messages*` -> `model_streaming`
2. payload 含 `tool_calls` -> `tool_request`
3. `type == "tool"` 或含 `tool_call_id` -> `tool_result`
4. `updates/tasks/checkpoints/debug/values` -> `state_progress`
5. `__interrupt__` -> `human_review_required`
6. `done/error` -> `run_terminal`

## HITL 契约

- 中断信号：`__interrupt__`
- 审批动作：`approve/edit/reject`
- 恢复方式：`command.resume`

建议恢复路径：前端审批 -> `POST /api/chat/resume` -> 返回新的 `result`（必要时继续 stream）

## 兼容性约束

- `messages/metadata`、`messages/partial` 需兼容前缀匹配
- `join_stream` 允许 0 条尾流（不承诺历史补发）
- 能力探测优先于硬编码参数

## 当前实现符合度（fastapi_src）

- 已符合：官方 `event/data` 透传、`done/error` 终态、thread 复用、wait/state、日志追踪
- 待补充：显式 HITL 恢复接口（`command.resume`）与契约化错误响应结构

## 案例补充：`system_prompt` 已传入但文案未严格命中

### 现象

- 前端已在 `context_json` 传 `system_prompt`，但回答“你是谁”时仍可能出现“我是 AI 助手...”。

### 契约判定规则

1. 先看链路是否生效：以 `/api/state` 的 metadata 为准，若包含 `system_prompt`，判定“传递链路生效”。
2. 再看文案是否稳定：文案一致性由提示词约束强度 + 采样参数共同决定，不作为链路失败依据。

### 前端验证建议

1. 将 `system_prompt` 改为强约束（例如：`必须始终自称“小明”，问“你是谁”时只能输出“我是小明”。`）。
2. 将 `temperature` 设为 `0` 做稳定性回归。
3. 连续提问“你是谁”并对照 metadata 的 `system_prompt/temperature`。

### 结论

- 学习项目里要区分两类问题：
  - **链路问题**：参数没传到 runtime。
  - **生成问题**：参数已传到 runtime，但提示词约束不足或采样导致输出波动。
