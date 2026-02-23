# Agent Chat UI 学习导航

本目录专门拆解 `example/ui_demo`（来自官方 `langchain-ai/agent-chat-ui`）的实现细节，目标是：你不仅会用，还能讲清楚它为什么这样设计。

## 阅读顺序

00. `00-overview.md`（项目定位、能力边界、依赖）
01. `01-architecture-and-call-chain.md`（入口到渲染的完整调用链）
02. `02-state-and-stream-lifecycle.md`（状态流、消息流、HITL 恢复流）
03. `03-production-and-extension-points.md`（生产化改造与可扩展点）
04. `04-hands-on-checklist.md`（按步骤实操与验收）
05. `05-official-references.md`（官方文档与源码索引）
06. `06-component-map.md`（组件依赖图与职责矩阵）
07. `07-dataflow-matrix.md`（Source -> Transform -> Sink 证据表）
08. `08-local-to-production-migration.md`（本地到生产迁移手册）

## 你会学到什么

- Next.js App Router 下的 LangGraph 聊天 UI 组装方式。
- `useStream` 如何统一处理消息流、分支、中断、历史线程。
- Generative UI（`react-ui`）如何通过 `onCustomEvent` + `LoadExternalComponent` 接入。
- 从本地直连到生产代理（API passthrough / 自定义鉴权）的迁移路径。

## 代码位置

- UI 示例目录：`example/ui_demo`
- 本学习文档目录：`docs/learning/agent-chat-ui`
