# 01. 最小页面范围

## 页面拆分

1. Chat Panel
- 展示用户输入与 AI 输出
- `messages*` 增量拼接渲染

2. Timeline Panel
- 展示 `updates/tasks/checkpoints/debug`
- 展示工具请求与工具结果

3. State Panel
- 展示 `/api/state` 快照
- 用于核对“输入是否沉淀到 thread”

## 交互约束

- 只接收后端透传的 `event/data`
- 不在前端改写事件含义
- 仅在 UI 层做分类显示
