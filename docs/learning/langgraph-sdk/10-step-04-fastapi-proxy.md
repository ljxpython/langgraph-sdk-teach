# Step 4：FastAPI 事件代理（学习辅助）

## 目标

- 用 FastAPI 把 LangGraph 事件流透传给前端。

## 任务

1. 提供 `POST /api/chat/start`（创建/返回 thread_id）
2. 提供 `GET /api/chat/stream`（SSE 转发 `runs.stream`）
3. 提供 `GET /api/chat/state`（读取 `threads.get_state`）

## 完成标准

- 浏览器能持续收到 SSE 事件，且 thread 状态可查询。
