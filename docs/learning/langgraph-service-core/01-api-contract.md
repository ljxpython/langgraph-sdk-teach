# 01. 最小 API 契约

## 接口清单

1. `POST /api/thread`：创建或复用 thread
2. `POST /api/chat/wait`：阻塞式调用
3. `POST /api/chat/resume`：提交 `command.resume` 恢复执行
4. `GET /api/chat/stream`：SSE 转发流事件
5. `GET /api/state`：读取 thread state
6. `GET /api/run-logs`：读取用户日志（wait/stream/resume）

## 契约要求

- `thread`：同一 `user_id` 返回稳定 `thread_id`
- `wait`：返回可读最终结果，且包含 `thread_id/run_id` 关联线索
- `stream`：逐条透传 `event/data`，结束发 `done`，异常发 `error`
- `state`：可回读消息与状态，验证“写回”是否生效
- `run_logs`：记录 wait/stream 的关键事件（用于排障与复盘）

## 兼容原则

- 不改写官方事件类型（`messages*`、`updates`、`tasks`、`checkpoints`、`debug` 等）
- `join_stream` 仅看加入后的尾流，不做历史补发承诺
