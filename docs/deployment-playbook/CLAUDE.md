# deployment-playbook Architecture

## Directory Tree

```text
docs/deployment-playbook/
├── README.md
└── CLAUDE.md
```

## File Responsibilities

- `README.md`: 统一说明本地开发与生产部署模式、架构图、推荐方案与落地顺序。
- `CLAUDE.md`: 记录本目录职责边界与文件定位，确保后续架构演进可追踪。

## Boundaries

- 仅讨论“开发/部署模式与调用边界”，不展开具体业务字段设计。
- 优先给出个人开发者可执行的最小生产方案。
- 明确区分 passthrough 通道与 Platform API 业务通道，避免 API 复刻。
