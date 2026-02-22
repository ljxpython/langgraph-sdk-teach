# FastAPI Service Core

这是学习项目里的服务层实现，目标是：**透传优先，少量二次改造**。

## 当前能力

- `POST /api/thread`：按 `user_id` 创建/复用 `thread_id`
- `POST /api/chat/wait`：调用 `runs.wait` 返回最终结果
- `POST /api/chat/resume`：提交 `command.resume` 恢复 HITL 流程
- `GET /api/chat/stream`：SSE 透传 `chunk.event/chunk.data`，补 `done/error`
- `GET /api/state`：回读 `threads.get_state`
- `run_logs`：写入 wait/stream 关键事件日志（SQLite）
- `logging`：统一日志模块 + 请求日志中间件（含 `x-request-id`）

## 目录结构

```text
fastapi_src/
├── app.py
├── api/routes.py
├── core/
│   ├── config.py
│   ├── langgraph_client.py
│   └── logging.py
├── db/sqlite.py
├── repositories/run_log_repo.py
├── repositories/thread_repo.py
├── services/
│   ├── chat_service.py
│   └── sse_service.py
└── models/schemas.py
```

## 启动

```bash
uv run langgraph dev --port 8123 --no-browser
uv run uvicorn fastapi_src.app:app --reload --port 8011
```

## 环境变量

- `LANGGRAPH_API_URL`（默认 `http://127.0.0.1:8123`）
- `LANGGRAPH_ASSISTANT_ID`（默认 `agent`）
- `FASTAPI_SQLITE_PATH`（默认 `fastapi_src/data/app.db`）
- `FASTAPI_DEFAULT_STREAM_MODE`（默认 `messages,updates,tasks,checkpoints,debug`）
- `FASTAPI_LOG_LEVEL`（默认 `INFO`）
- `FASTAPI_CORS_ORIGINS`（保留配置项；当前默认策略为 `*` 以简化本地联调）

## 日志与排障

- 每次请求会记录 `request.started` / `request.completed` / `request.failed`
- 响应头会附带 `x-request-id`，用于前后端联动排查
- `run_logs` 会记录 wait/stream 的关键事件（`event/status/error`）

## 测试

```bash
uv run --with pytest pytest tests/fastapi_test -vv -s
```

## 下一步建议（还可补充）

1. 为 `run_logs` 增加查询接口（按 user_id/run_id 过滤）。
2. 增加 `/healthz` 与 `/readyz` 健康检查接口。
3. 为 `/api/chat/stream` 增加可选 `join_stream` 恢复入口。
4. 增加参数校验与错误码规范（统一错误结构）。
5. 增加最小鉴权中间件（例如固定 token），方便前端联调演练。
