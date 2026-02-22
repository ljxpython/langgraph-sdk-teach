# 03. 错误与重试

## 错误分层

- 传输层：SSE 断流、网络超时
- 运行层：`error` 事件
- 交互层：`__interrupt__` 未恢复导致流程停在人工审批

## 最小重试策略

1. `wait` 失败：记录 `thread_id/run_id` 后重试一次
2. `stream` 断流：优先 `join_stream` 接尾流
3. 命中 `__interrupt__`：优先展示决策 UI，不自动跳过

## 不可省日志字段

- `thread_id`
- `run_id`
- `event`
- `error message`
