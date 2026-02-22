# Step 4：FastAPI 事件代理（已并入服务主线）

> 该步骤已并入独立目录 `docs/learning/langgraph-service-core/`。

请改看：

- 契约定义：`docs/learning/langgraph-service-core/01-api-contract.md`
- SSE 消费：`docs/learning/langgraph-service-core/02-sse-consume-model.md`
- 验收方式：`docs/learning/langgraph-service-core/04-verification.md`

说明：

- 本项目坚持最小能力主线：thread/wait/stream/state + done/error。
- 事件消费优先官方 SDK 类型（`chunk.event` / `chunk.data` / `__interrupt__`）。
