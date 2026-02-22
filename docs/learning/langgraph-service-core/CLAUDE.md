# langgraph-service-core Architecture

## Directory Tree

```text
docs/learning/langgraph-service-core/
├── README.md
├── 00-overview.md
├── 01-api-contract.md
├── 02-sse-consume-model.md
├── 03-error-and-retry.md
└── 04-verification.md
```

## File Responsibilities

- `README.md`: 服务主线入口与阅读顺序。
- `00-overview.md`: 学习目标、边界与非目标。
- `01-api-contract.md`: 最小四接口契约与请求响应结构。
- `02-sse-consume-model.md`: 前端状态机与官方事件类型消费规则。
- `03-error-and-retry.md`: 失败语义、重试与恢复策略。
- `04-verification.md`: curl/pytest 验收脚本与通过标准。

## Boundaries

- 仅覆盖服务集成最小能力：thread、wait、stream、state、done/error。
- 不定义自有业务协议，优先消费 LangGraph SDK 官方 `event/data/__interrupt__`。
