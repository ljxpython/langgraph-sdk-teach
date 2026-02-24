# 10. 接口全量盘点与业务映射

本篇专门回答你提的“`ui_demo` 涉及哪些接口，以及它们对应什么业务”。

## 1) 盘点范围

- 代码范围：`example/ui_demo/src/**`
- 盘点对象：
  1) 直接 HTTP 调用（代码里明确 `fetch`）
  2) SDK 调用（`useStream`/`Client`/`submit` 等）
  3) Next.js `/api` 代理暴露的方法
  4) 与当前功能强相关的官方 Agent Server URL

## 2) 直接 HTTP 接口（代码显式）

1. `GET {apiUrl}/info`
   - 代码：`example/ui_demo/src/providers/Stream.tsx:57`
   - 业务：启动后做连通性与权限检查；失败时弹 toast 提示。

> 结论：`ui_demo` 里明确手写的 HTTP 调用只有这一处。

## 3) SDK 调用 -> 对应业务 -> 典型 URL

## 3.1 明确可映射到 URL 的调用

1. `client.threads.search({...})`
   - 代码：`example/ui_demo/src/providers/Thread.tsx:46`
   - 业务：线程历史列表查询
   - 对应 URL：`POST {apiUrl}/threads/search`

2. `stream.submit(payload, options)`（普通发送）
   - 代码：`example/ui_demo/src/components/thread/index.tsx:217`
   - 业务：发送一条用户消息并流式获取 Assistant 输出
   - 对应 URL：`POST {apiUrl}/threads/{thread_id}/runs/stream`

3. `stream.submit(undefined, { checkpoint, ... })`（重生成）
   - 代码：`example/ui_demo/src/components/thread/index.tsx:245`
   - 业务：基于父 checkpoint 重跑 AI 回复
   - 对应 URL：`POST {apiUrl}/threads/{thread_id}/runs/stream`

4. `thread.submit({ messages:[newMessage] }, { checkpoint, ... })`（编辑后重提）
   - 代码：`example/ui_demo/src/components/thread/messages/human.tsx:56`
   - 业务：编辑历史 Human 消息并从对应分支回放
   - 对应 URL：`POST {apiUrl}/threads/{thread_id}/runs/stream`

5. `thread.submit({}, { command:{ resume:{ decisions }}})`（HITL 恢复）
   - 代码：
     - `example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:89`
     - `example/ui_demo/src/components/thread/agent-inbox/components/thread-actions-view.tsx:178`
     - `example/ui_demo/src/components/thread/agent-inbox/components/thread-actions-view.tsx:225`
   - 业务：中断审批（approve/edit/reject）后恢复执行
   - 对应 URL：`POST {apiUrl}/threads/{thread_id}/runs/stream`

6. `thread.submit({}, { command:{ goto: END }})`（HITL 直接结束）
   - 代码：`example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:191`
   - 业务：Mark as Resolved，跳过后续执行
   - 对应 URL：`POST {apiUrl}/threads/{thread_id}/runs/stream`

## 3.2 运行时方法（SDK 内部处理，不在 UI 里直接给 URL）

1. `stream.stop()`
   - 代码：`example/ui_demo/src/components/thread/index.tsx:522`
   - 业务：取消当前流式输出

2. `thread.setBranch(branch)`
   - 代码：
     - `example/ui_demo/src/components/thread/messages/ai.tsx:202`
     - `example/ui_demo/src/components/thread/messages/human.tsx:131`
   - 业务：切换历史分支

3. `thread.getMessagesMetadata(message)`
   - 代码：
     - `example/ui_demo/src/components/thread/messages/ai.tsx:123`
     - `example/ui_demo/src/components/thread/messages/human.tsx:45`
   - 业务：读取 checkpoint/branch 元数据，支撑 regenerate/edit/branch UI

## 4) `/api` 代理层暴露接口（生产模式）

文件：`example/ui_demo/src/app/api/[..._path]/route.ts`

1. 已配置 `LANGGRAPH_API_URL` 时，透传：
   - `GET/POST/PUT/PATCH/DELETE/OPTIONS /api/*`
2. 未配置 `LANGGRAPH_API_URL` 时：
   - `GET/POST/PUT/PATCH/DELETE` -> 返回 `500` + 友好错误 JSON
   - `OPTIONS` -> 返回 `204`
3. 运行时：`edge`

## 5) 与 `ui_demo` 强相关的官方 Agent Server URL

1. `POST /threads/search`（线程检索）
2. `POST /threads`（创建线程）
3. `POST /threads/{thread_id}/runs/stream`（创建流式 run）
4. `GET /threads/{thread_id}/runs/{run_id}/stream`（加入已存在 run 流）
5. `GET /threads/{thread_id}/history`（线程历史状态）
6. `GET /threads/{thread_id}/state`（线程最新状态）

> 说明：`ui_demo` 代码里没有手写这些 URL 字符串，主要通过 SDK 方法间接触发。

## 6) 场景 -> 接口一图看懂

```text
发送消息
  UI: handleSubmit
  SDK: stream.submit(payload, options)
  API: POST /threads/{thread_id}/runs/stream

重生成
  UI: handleRegenerate
  SDK: stream.submit(undefined, {checkpoint,...})
  API: POST /threads/{thread_id}/runs/stream

编辑消息
  UI: HumanMessage.handleSubmitEdit
  SDK: thread.submit({messages:[...]}, {checkpoint,...})
  API: POST /threads/{thread_id}/runs/stream

中断恢复/结束
  UI: AgentInbox
  SDK: thread.submit({command.resume}) / thread.submit({command.goto})
  API: POST /threads/{thread_id}/runs/stream

历史线程
  UI: ThreadHistory
  SDK: client.threads.search(...)
  API: POST /threads/search
```

## 7) 学习建议（接口视角）

1. 先看 `Thread.tsx` 的 `handleSubmit`，理解“为什么所有业务最终都走 `runs/stream`”。
2. 再看 `agent-inbox`，理解 `command.resume/goto` 只是同一个接口的不同 body。
3. 最后看 `route.ts`，理解本地直连与生产代理只是 `apiUrl` 不同，业务语义不变。

## 8) 为什么你会感觉“几乎只有 /threads”

这个感觉是对的。`ui_demo` 是“聊天会话 UI”，它以 **thread 作为状态容器**，所以主链天然集中在：

1. `threads.search`（找会话）
2. `threads.create`（建会话）
3. `threads/{id}/runs/stream`（在会话上执行）
4. `threads/{id}/history|state`（恢复/回放）

从 SDK 源码也能看到 `useStream` 主流程就是：

- 无 `threadId` 时 `client.threads.create(...)`
- 提交时 `client.runs.stream(threadId, assistantId, ...)`
- 历史恢复时 `client.threads.getHistory(...)` / `client.threads.getState(...)`

（参考：`langchain-ai/langgraphjs` 的 `libs/sdk/src/react/stream.lgp.tsx`）

## 9) “其他接口族”在 ui_demo 的状态

下面这些接口族在 SDK 里存在，但 **ui_demo 当前对话流程未直接使用**：

1. `/assistants/*`
   - 用于 assistant 生命周期管理（创建、更新、搜索、图 schema）。
   - ui_demo 只消费 `assistantId` 作为运行参数，不在前端管理 assistant 资源。

2. `/runs/crons/*`
   - 用于定时/后台任务。
   - ui_demo 是交互式聊天，不涉及 cron 调度。

3. `/store/*`、`/a2a/*`、`/mcp/*`
   - 分别用于 KV 存储、Agent-to-Agent 协议、MCP 暴露。
   - ui_demo 作为通用聊天前端模板，未在页面层接这些能力。

结论：你看到的接口“偏 threads”不是漏写，而是该 demo 的产品定位决定的。

## 10) 全接口族对照总表（Agent Server vs ui_demo）

```text
+------------------+--------------------------+--------------------+-----------------------------------------------+
| 接口族           | 典型 URL                 | ui_demo 使用状态   | 若要接入，优先改动文件                         |
+------------------+--------------------------+--------------------+-----------------------------------------------+
| system           | GET /info                | 已使用（直连检查） | src/providers/Stream.tsx                       |
| threads          | POST /threads/search     | 已使用（核心）     | src/providers/Thread.tsx                       |
| thread-runs      | POST /threads/{id}/runs/ | 已使用（核心）     | src/components/thread/index.tsx                |
|                  | stream                   |                    | src/components/thread/messages/human.tsx       |
|                  |                          |                    | src/components/thread/agent-inbox/**           |
| thread-runs join | GET /threads/{id}/runs/  | 间接涉及（SDK）    | src/providers/Stream.tsx                       |
|                  | {run_id}/stream          |                    |                                                |
| thread-state     | GET /threads/{id}/state  | 间接涉及（SDK）    | src/providers/Stream.tsx                       |
| thread-history   | GET/POST /threads/{id}/  | 间接涉及（SDK）    | src/providers/Stream.tsx                       |
|                  | history                  |                    |                                                |
| assistants       | /assistants/*            | 未使用             | src/providers/Thread.tsx（检索条件联动）       |
|                  |                          |                    | src/providers/Stream.tsx（assistant 选择器）   |
|                  |                          |                    | 新增页面: src/app/(or components)/assistants/*|
| crons            | /runs/crons/*            | 未使用             | 新增页面: src/app/(or components)/crons/*      |
| store            | /store/*                 | 未使用             | 新增 provider + 新增 UI 模块                   |
| a2a              | /a2a/*                   | 未使用             | 新增集成层（服务发现/对端会话）                |
| mcp              | /mcp/*                   | 未使用             | 新增工具管理页 + 鉴权配置                       |
+------------------+--------------------------+--------------------+-----------------------------------------------+
```

注：`thread-runs join`、`thread-state`、`thread-history` 在 ui_demo 中主要由 `useStream` 内部流程触发，不是页面层手写 URL。
