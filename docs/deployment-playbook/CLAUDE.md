# deployment-playbook Architecture

## Directory Tree

```text
docs/deployment-playbook/
├── 01-thread-identity-isolation-playbook.md
├── 02-platform-langgraph-global-interaction-model.md
├── 03-manageable-capabilities-via-passthrough.md
├── 04-postgres-vs-mysql-vs-sqlite.md
├── README.md
└── CLAUDE.md
```

## File Responsibilities

- `README.md`: 统一说明本地开发与生产部署模式、架构图、推荐方案与落地顺序。
- `01-thread-identity-isolation-playbook.md`: 记录线程归属、会话映射、用户隔离与平台-LangGraph 交互边界。
- `02-platform-langgraph-global-interaction-model.md`: 定义全局交互面、通信契约、幂等顺序、错误模型和扩展路径。
- `03-manageable-capabilities-via-passthrough.md`: 汇总可查询/可修改能力矩阵，并给出透传管理的控制强度与落地建议。
- `04-postgres-vs-mysql-vs-sqlite.md`: 对比数据库在平台与 LangGraph 场景中的使用差异与选型建议。
- `CLAUDE.md`: 记录本目录职责边界与文件定位，确保后续架构演进可追踪。

## Boundaries

- 仅讨论“开发/部署模式与调用边界”，不展开具体业务字段设计。
- 优先给出个人开发者可执行的最小生产方案。
- 明确区分 passthrough 通道与 Platform API 业务通道，避免 API 复刻。
