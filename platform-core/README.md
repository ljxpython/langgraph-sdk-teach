# platform-core

`platform-core` 是平台统一入口层：负责 `threads/runs/assistants` 受控兼容接口，以及 run 级治理日志查询。

## Quick Start

1. 配置环境变量：

```bash
export PLATFORM_CORE_UPSTREAM_URL="http://127.0.0.1:8123"
export PLATFORM_CORE_TIMEOUT="30"
export PLATFORM_CORE_LOG_LEVEL="INFO"
```

2. 启动服务（`src` 布局）：

```bash
uv run uvicorn src.app.main:app --port 8011
```

3. 健康检查：

```bash
curl -i http://127.0.0.1:8011/healthz
```

## Identity Model

- 当前本地联调阶段默认关闭鉴权；无 `Authorization` 头也可访问。
- 若携带 `Authorization: Bearer tenant:<tenant_id>;user:<user_id>`，服务仍会解析并用于数据隔离。
- 若携带非法 `Authorization` 头，服务会返回 `401`。

## Stop Service

推荐用 PID 文件方式启动和停止：

```bash
# start
uv run uvicorn src.app.main:app --port 8011 > /tmp/platform-core.log 2>&1 &
echo $! > /tmp/platform-core.pid

# stop
if [ -f /tmp/platform-core.pid ]; then
  kill "$(cat /tmp/platform-core.pid)" 2>/dev/null || true
  rm -f /tmp/platform-core.pid
fi
```

如果 PID 文件丢失，可按端口停止：

```bash
pids="$(lsof -ti:8011)"; [ -n "$pids" ] && kill $pids
```

## Controlled API Surface

受控放行接口（首版）：

- `POST /assistants/search`
- `GET /assistants/{assistant_id}`
- `POST /threads`
- `POST /threads/search`
- `GET /threads/{thread_id}`
- `GET /threads/{thread_id}/state`
- `POST /threads/{thread_id}/runs/wait`
- `POST /threads/{thread_id}/runs/stream`
- `GET /threads/{thread_id}/runs/{run_id}/join`
- `GET /run-logs?platform_session_id=<uuid>`
- `GET /run-logs?run_id=<uuid>`

## Security Boundaries

- 请求体禁止透传危险字段，包含 `api_url`、非声明字段、伪造 `thread_id`
- 参数错误统一按标准错误结构返回：`code/message/trace_id`
- 上游内部异常不会暴露堆栈细节

## Governance Logging

每次 run 会记录并可查询以下字段：

- `trace_id`
- `tenant_id`
- `user_id`
- `platform_session_id`
- `thread_id`
- `run_id`
- `status`
- `latency`
- `created_at`

## Compatibility With platform-web

- `platform-web` 接入无需改业务代码。
- 只需把前端 API 目标 URL 切到 `platform-core`。
- 前端不应直连 LangGraph 服务。
