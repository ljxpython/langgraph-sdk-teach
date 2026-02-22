# 服务集成与可观测调试（迁移入口）

> 本文已迁移到独立服务主线，避免与 SDK 主线混杂。

请改为从这里开始：

- `docs/learning/langgraph-service-core/README.md`

建议阅读顺序：

1. `docs/learning/langgraph-service-core/00-overview.md`
2. `docs/learning/langgraph-service-core/01-api-contract.md`
3. `docs/learning/langgraph-service-core/02-sse-consume-model.md`
4. `docs/learning/langgraph-service-core/03-error-and-retry.md`
5. `docs/learning/langgraph-service-core/04-verification.md`

保留说明：

- 当前推荐实现：`fastapi_src/app.py`
- 历史示例保留：`sdk_src/examples/langgraph_fastapi_observer.py`
- 核心接口仍是 `/api/thread` `/api/chat/wait` `/api/chat/stream` `/api/state`
