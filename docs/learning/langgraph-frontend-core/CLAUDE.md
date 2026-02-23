# langgraph-frontend-core Architecture

## Directory Tree

```text
docs/learning/langgraph-frontend-core/
├── README.md
├── 00-overview.md
├── 01-ui-scope.md
├── 02-event-to-ui-mapping.md
├── 03-hitl-interaction.md
├── 04-verification.md
├── 05-init-and-structure-plan.md
├── 06-frontend-backend-contract-v1.md
├── 07-platform-ui-design.md
├── 08-ui-refactor-checklist.md
├── 09-ai-platform-core-feature-and-call-chain.md
├── 10-controls-field-and-call-mapping.md
├── 11-platform-replication-playbook.md
└── 12-thinking-observability-adaptation.md
```

## File Responsibilities

- `README.md`: 前端主线入口与学习顺序。
- `00-overview.md`: 前端学习目标、边界和非目标。
- `01-ui-scope.md`: 最小页面范围（Chat/Timeline/State）。
- `02-event-to-ui-mapping.md`: 官方事件类型到前端行为映射。
- `03-hitl-interaction.md`: `__interrupt__` 审批交互与恢复流程。
- `04-verification.md`: 手工验收与回归清单。
- `05-init-and-structure-plan.md`: 前端初始化与目录落地计划。
- `06-frontend-backend-contract-v1.md`: 前后端联调契约与字段约定。
- `07-platform-ui-design.md`: 平台化 UI 设计方向与布局策略。
- `08-ui-refactor-checklist.md`: 迭代改造项与执行清单。
- `09-ai-platform-core-feature-and-call-chain.md`: 平台功能优先级与接口链路总览。
- `10-controls-field-and-call-mapping.md`: Controls 字段生效范围与点击到接口映射。
- `11-platform-replication-playbook.md`: 平台能力复刻步骤、接口模板与验收标准。
- `12-thinking-observability-adaptation.md`: Thinking 可视化能力边界、字段映射与适配策略。

## Boundaries

- 只做学习项目最小能力，不追求产品级 UI。
- 所有语义判定优先使用官方输出，不发明新协议层。
