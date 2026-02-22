# LangGraph Frontend Core 学习导航

这是前端最小实践主线，目标是把官方 streaming 语义稳定映射到前端 UI 行为。

## 阅读顺序

00. `00-overview.md`（目标与边界）
01. `01-ui-scope.md`（最小页面能力）
02. `02-event-to-ui-mapping.md`（事件到 UI 映射）
03. `03-hitl-interaction.md`（人工审批交互）
04. `04-verification.md`（验收清单）
05. `05-init-and-structure-plan.md`（初始化与目录落地计划）
06. `06-frontend-backend-contract-v1.md`（联调契约 v1）

## 设计原则

- 前端只消费官方类型：`event` / `data` / `__interrupt__`
- 不自定义业务事件协议
- 先做最小可观测与可调试，不做复杂视觉系统

## 代码目录（落地约定）

- 前端代码根目录：`frontend_src/`
- 与 `fastapi_src/`、`docs/learning/` 平级
