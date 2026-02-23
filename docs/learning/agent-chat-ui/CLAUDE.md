# agent-chat-ui Learning Docs Architecture

## Directory Tree

```text
docs/learning/agent-chat-ui/
├── README.md
├── 00-overview.md
├── 01-architecture-and-call-chain.md
├── 02-state-and-stream-lifecycle.md
├── 03-production-and-extension-points.md
├── 04-hands-on-checklist.md
├── 05-official-references.md
├── 06-component-map.md
├── 07-dataflow-matrix.md
├── 08-local-to-production-migration.md
└── CLAUDE.md
```

## File Responsibilities

- `README.md`: 学习入口与阅读顺序。
- `00-overview.md`: 项目定位、核心能力、配置模型与依赖结构。
- `01-architecture-and-call-chain.md`: 从入口到渲染的主调用链分解。
- `02-state-and-stream-lifecycle.md`: query/localStorage/env 与 stream 运行态协同机制。
- `03-production-and-extension-points.md`: 生产化迁移路径与可扩展改造点清单。
- `04-hands-on-checklist.md`: 可执行的实操步骤与验收标准。
- `05-official-references.md`: 官方文档、源码与生产化资料索引。
- `06-component-map.md`: 组件依赖关系、层级职责与复用设计。
- `07-dataflow-matrix.md`: 关键流程的 Source/Transform/Sink 证据化拆解。
- `08-local-to-production-migration.md`: 从本地直连迁移到生产鉴权的落地步骤。
- `CLAUDE.md`: 本目录结构与职责边界说明。

## Boundaries

- 只解释 `example/ui_demo` 的官方实现与可扩展路径。
- 不引入与当前代码无关的业务协议设计。
- 优先基于代码证据，不做推测式结论。
