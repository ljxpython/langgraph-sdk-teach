# langgraph-frontend-core Architecture

## Directory Tree

```text
docs/learning/langgraph-frontend-core/
├── README.md
├── 00-overview.md
├── 01-ui-scope.md
├── 02-event-to-ui-mapping.md
├── 03-hitl-interaction.md
└── 04-verification.md
```

## File Responsibilities

- `README.md`: 前端主线入口与学习顺序。
- `00-overview.md`: 前端学习目标、边界和非目标。
- `01-ui-scope.md`: 最小页面范围（Chat/Timeline/State）。
- `02-event-to-ui-mapping.md`: 官方事件类型到前端行为映射。
- `03-hitl-interaction.md`: `__interrupt__` 审批交互与恢复流程。
- `04-verification.md`: 手工验收与回归清单。

## Boundaries

- 只做学习项目最小能力，不追求产品级 UI。
- 所有语义判定优先使用官方输出，不发明新协议层。
