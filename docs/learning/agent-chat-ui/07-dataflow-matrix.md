# 07. Source -> Transform -> Sink 证据表

## 1) 连接配置流

- Source
  - query `apiUrl` / `assistantId`：`example/ui_demo/src/providers/Stream.tsx:169`, `example/ui_demo/src/providers/Stream.tsx:172`
  - env 回退：`example/ui_demo/src/providers/Stream.tsx:164`, `example/ui_demo/src/providers/Stream.tsx:166`
  - localStorage API key：`example/ui_demo/src/lib/api-key.tsx:1`
- Transform
  - 组装 `finalApiUrl` / `finalAssistantId`：`example/ui_demo/src/providers/Stream.tsx:188`
  - `setApiKey` 写回本地：`example/ui_demo/src/providers/Stream.tsx:182`
- Sink
  - 注入 `useTypedStream({...})`：`example/ui_demo/src/providers/Stream.tsx:103`

## 2) threadId 生命周期

- Source
  - stream 回调 `onThreadId`：`example/ui_demo/src/providers/Stream.tsx:117`
  - 历史点击 `setThreadId(t.thread_id)`：`example/ui_demo/src/components/thread/history/index.tsx:53`
  - 新线程置空：`example/ui_demo/src/components/thread/index.tsx:147`
- Transform
  - query 参数更新 -> 运行上下文切换
- Sink
  - `useStream` 的 `threadId: threadId ?? null`：`example/ui_demo/src/providers/Stream.tsx:107`
  - 历史恢复开关 `fetchStateHistory: true`：`example/ui_demo/src/providers/Stream.tsx:108`

## 3) 用户发送消息流

- Source
  - `input` + `contentBlocks`：`example/ui_demo/src/components/thread/index.tsx:127`
  - 多模态 blocks 来自 `useFileUpload`：`example/ui_demo/src/hooks/use-file-upload.tsx:18`
- Transform
  - 构造 human message：`example/ui_demo/src/components/thread/index.tsx:203`
  - 补 tool response：`example/ui_demo/src/components/thread/index.tsx:212`
  - 规则函数：`example/ui_demo/src/lib/ensure-tool-responses.ts:6`
- Sink
  - `stream.submit(payload, options)`：`example/ui_demo/src/components/thread/index.tsx:217`
  - options 含 `streamMode/streamSubgraphs/streamResumable/optimisticValues`

## 4) regenerate 与 edit 流

- regenerate
  - Source: 点击刷新按钮（AI 消息操作条）
  - Transform: 从 metadata 读取 parent checkpoint：`example/ui_demo/src/components/thread/messages/ai.tsx:126`
  - Sink: `submit(undefined, { checkpoint })`：`example/ui_demo/src/components/thread/index.tsx:245`
- edit
  - Source: human 消息进入编辑态
  - Transform: 生成新 human message + parent checkpoint：`example/ui_demo/src/components/thread/messages/human.tsx:46`
  - Sink: `thread.submit({messages:[newMessage]}, ...)`：`example/ui_demo/src/components/thread/messages/human.tsx:56`

## 5) interrupt 决策流

- Source
  - `thread.interrupt`：`example/ui_demo/src/components/thread/messages/ai.tsx:124`
  - schema 判定：`example/ui_demo/src/lib/agent-inbox-interrupt.ts:4`
- Transform
  - 命中 inbox schema -> `ThreadView`
  - 非 inbox -> `GenericInterruptView`
- Sink
  - 单 action resume：`example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:89`
  - resolve（`goto: END`）：`example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:191`
  - 多 action 批量 resume：`example/ui_demo/src/components/thread/agent-inbox/components/thread-actions-view.tsx:225`

## 6) 分支切换流

- Source
  - `getMessagesMetadata(message)`：
    - `example/ui_demo/src/components/thread/messages/ai.tsx:123`
    - `example/ui_demo/src/components/thread/messages/human.tsx:45`
- Transform
  - `BranchSwitcher` 在 options 中算前后分支：`example/ui_demo/src/components/thread/messages/shared.tsx:89`
- Sink
  - `thread.setBranch(branch)`：
    - `example/ui_demo/src/components/thread/messages/ai.tsx:202`
    - `example/ui_demo/src/components/thread/messages/human.tsx:131`

## 7) Generative UI 自定义事件流

- Source
  - stream custom event：`example/ui_demo/src/providers/Stream.tsx:109`
- Transform
  - `isUIMessage/isRemoveUIMessage` 判定并 `uiMessageReducer` 归并：`example/ui_demo/src/providers/Stream.tsx:110`
- Sink
  - `values.ui` 过滤到当前消息：`example/ui_demo/src/components/thread/messages/ai.tsx:27`
  - `LoadExternalComponent` 渲染：`example/ui_demo/src/components/thread/messages/ai.tsx:35`

## 8) 生产代理流

- Source
  - `LANGGRAPH_API_URL` / `LANGSMITH_API_KEY`：`example/ui_demo/src/app/api/[..._path]/route.ts:7`
- Transform
  - `initApiPassthrough({...})` 构建 handler
- Sink
  - 前端请求 `/api/*` 由 Next 路由转发到 LangGraph

## 9) 一句话理解

这个项目把“配置状态（query/env/localStorage）”和“运行状态（stream/messages/interrupt）”分层管理，再通过组件分发把复杂语义拆成独立渲染单元，所以它既适合学习，也适合直接改造成生产骨架。
