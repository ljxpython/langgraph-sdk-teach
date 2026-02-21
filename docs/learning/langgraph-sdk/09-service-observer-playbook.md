# 服务集成与可观测调试（FastAPI + LangGraph）

这是下一阶段学习：把你已掌握的 API 能力放进“真实服务形态”。

## 学习目标

- 把 LangGraph 调用接入你自己的 FastAPI 服务
- 同时支持 `wait` 与 `stream` 两种输出方式
- 能从前端/CLI 看到每个步骤事件

## 对应代码

- `sdk_src/examples/langgraph_fastapi_observer.py`

核心接口：

- `POST /api/thread`：创建或复用 thread
- `POST /api/chat/wait`：阻塞式调用
- `GET /api/chat/stream`：SSE 流式事件
- `GET /api/state`：读取线程 state

## 启动方式

先启动 LangGraph：

```bash
uv run langgraph dev --port 8123 --no-browser
```

再启动学习服务：

```bash
uv run uvicorn sdk_src.examples.langgraph_fastapi_observer:app --reload --port 8011
```

## 验证步骤（按顺序）

### 1) 创建线程

```bash
curl -s -X POST http://127.0.0.1:8011/api/thread \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u-demo"}'
```

### 2) 阻塞式调用

```bash
curl -s -X POST http://127.0.0.1:8011/api/chat/wait \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"u-demo",
    "message":"你好，给我三条学习建议",
    "assistant_id":"agent",
    "context":{"model_provider":"kimi","enable_local_tools":false,"enable_local_mcp":true,"mcp_servers":["local_math"]}
  }'
```

### 3) 流式调用（SSE）

```bash
curl -N "http://127.0.0.1:8011/api/chat/stream?user_id=u-demo&assistant_id=agent&message=请先算2%2B3再输出结果&context_json=%7B%22model_provider%22%3A%22kimi%22%2C%22enable_local_tools%22%3Afalse%2C%22enable_local_mcp%22%3Atrue%2C%22mcp_servers%22%3A%5B%22local_math%22%5D%7D"
```

### 4) 读取 state

```bash
curl -s "http://127.0.0.1:8011/api/state?user_id=u-demo"
```

## 重点观察

- `thread_id` 是否稳定复用
- SSE 中是否有 `messages/updates/tasks/checkpoints`
- state 是否持续增长（对话记忆是否写回）

## 这一步学完后你会得到什么

- 你已经不是“会调 SDK”，而是“会做服务集成”
- 下一步就可以进入前端观察面板或生产治理（鉴权、日志、限流）
