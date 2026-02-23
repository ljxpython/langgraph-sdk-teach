# 07. 平台化 UI 设计方案（核心版）

## 目标

在不增加过多复杂度的前提下，让学习项目前端具备“通用 AI 平台”的信息架构和交互体验。

## 设计原则

1. 功能最小化：只保留高频能力，不做企业级扩展。
2. 语义标准化：只消费官方 `event/data/__interrupt__`。
3. 可观测优先：每次 run 都能被前端完整追踪。

## 信息架构（IA）

### 三栏布局

1. 左栏：Session Workspace
- 会话列表
- 新建会话
- 切换当前会话

2. 中栏：Chat Workspace
- 输入框与发送按钮
- AI 流式文本
- 最终消息列表

3. 右栏：Controls + Observability
- 参数面板（assistant/system prompt/temperature）
- 时间线（messages/tool/updates/checkpoints/debug）
- HITL 审批（approve/edit/reject）
- Debug logs（thread_id/run_id/request_id）

## 最小功能集合（MVP）

1. 会话管理（新建/切换）
2. 流式聊天（SSE）
3. 事件分类时间线
4. HITL 恢复（resume）
5. state 回读与 run_logs 调试

## 视觉策略

- 中性色卡片布局（浅背景 + 细边框）
- 事件徽章（ai_stream/tool/state_progress/run_terminal）
- 稳定的顶部栏（项目名、环境、连接状态）

## 验收标准

1. 一眼能看清“会话/对话/调试”三大区域。
2. 一次请求可完整看到输入 -> 流式 -> 工具 -> 终态。
3. 命中中断时能在页面审批恢复，不依赖控制台。
