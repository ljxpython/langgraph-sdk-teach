# 09. Assistant 对话逻辑全景

这篇专门回答 5 个问题：

1. 对话逻辑由哪个页面管理？
2. 主要调用了哪些接口？
3. 完整对话链路怎么跑？
4. 实现了哪些功能与场景？
5. 关键流程图是什么？

## 1) 对话逻辑由哪里管理

## 1.1 页面装配入口

- `example/ui_demo/src/app/page.tsx`
- 作用：只负责组装上下文，不直接写对话业务逻辑。
- 组合顺序：`ThreadProvider -> StreamProvider -> ArtifactProvider -> Thread`

## 1.2 对话业务主控

- `example/ui_demo/src/components/thread/index.tsx`
- 这是对话“主编排页”：
  - 输入与提交（`handleSubmit`）
  - 重生成（`handleRegenerate`）
  - 中断流停止（`stream.stop()`）
  - 消息列表渲染（Human/Assistant）
  - 历史侧栏、工具显示开关、上传入口

## 1.3 运行态管理

- `example/ui_demo/src/providers/Stream.tsx`
- 通过 `useStream` 建立运行态，管理：
  - `messages/values/interrupt/isLoading/error`
  - `threadId` 同步
  - `onCustomEvent` 处理 Generative UI
  - `fetchStateHistory` 历史恢复

## 2) 主要调用接口与 SDK 调用点

## 2.1 前端直连 / SDK 封装调用

1. `stream.submit(...)`
   - 用户发送消息：`example/ui_demo/src/components/thread/index.tsx:217`
   - AI 重生成：`example/ui_demo/src/components/thread/index.tsx:245`
   - HITL resume：`example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:89`

2. `stream.stop()`
   - 取消当前流式输出：`example/ui_demo/src/components/thread/index.tsx:522`

3. `thread.setBranch(branch)`
   - 分支切换：`example/ui_demo/src/components/thread/messages/ai.tsx:202`

4. `client.threads.search(...)`
   - 历史线程检索：`example/ui_demo/src/providers/Thread.tsx:46`

## 2.2 直接 HTTP 调用点

1. `GET {apiUrl}/info`
   - 连通性检查：`example/ui_demo/src/providers/Stream.tsx:57`

2. `GET/POST/PUT/PATCH/DELETE/OPTIONS /api/*`（可选代理）
   - 路由定义：`example/ui_demo/src/app/api/[..._path]/route.ts:30`
   - 后端转发目标：`LANGGRAPH_API_URL`

> 说明：具体 runs/stream 等路径由 `@langchain/langgraph-sdk` 内部封装，不在 UI 代码里硬编码。

## 2.3 SDK 背后对应的 LangGraph URL（重点）

下面把 `ui_demo` 常见 SDK 调用，展开成服务端 URL 形态（`{apiUrl}` 为你填写的部署地址，或 `/api` 代理地址）。

1. 健康检查（UI 自己直接调）
   - `GET {apiUrl}/info`
   - 代码：`example/ui_demo/src/providers/Stream.tsx:57`

2. 线程列表检索（`client.threads.search`）
   - `POST {apiUrl}/threads/search`
   - 代码：`example/ui_demo/src/providers/Thread.tsx:46`
   - API 文档：`/agent-server-api/threads/search-threads`

3. 创建线程（SDK 在需要时创建）
   - `POST {apiUrl}/threads`
   - API 文档：`/agent-server-api/threads/create-thread`

4. 在线程上创建流式 run（`stream.submit` 的核心目标）
   - `POST {apiUrl}/threads/{thread_id}/runs/stream`
   - 代码调用入口：`example/ui_demo/src/components/thread/index.tsx:217`
   - API 文档：`/agent-server-api/thread-runs/create-run-stream-output`

5. 恢复/加入某次 run 的 SSE（对应 join 能力）
   - `GET {apiUrl}/threads/{thread_id}/runs/{run_id}/stream`
   - API 文档：`/agent-server-api/thread-runs/join-run-stream`

6. 获取线程历史状态（`fetchStateHistory` 相关能力）
   - `GET {apiUrl}/threads/{thread_id}/history`
   - API 文档：`/agent-server-api/threads/get-thread-history`

7. 获取线程最新状态
   - `GET {apiUrl}/threads/{thread_id}/state`
   - API 文档：`/agent-server-api/threads/get-thread-state`

### 2.4 你在本项目里可以这样理解 URL

1. 本地直连：`apiUrl = http://localhost:2024`
2. 生产代理：`apiUrl = https://your-site/api`（由 `example/ui_demo/src/app/api/[..._path]/route.ts` 转发）
3. 所以上面的 URL 会变成：
   - 直连：`http://localhost:2024/threads/search`
   - 代理：`https://your-site/api/threads/search`

### 2.5 三类 `submit` 在 URL 层的差异

```text
普通发送
  stream.submit({messages, context}, options)
  -> POST /threads/{thread_id}/runs/stream

重生成（regenerate）
  stream.submit(undefined, { checkpoint, ... })
  -> POST /threads/{thread_id}/runs/stream
  （同一路径，不同 body: 带 checkpoint）

中断恢复/结束（HITL）
  thread.submit({}, { command: { resume: {...} } })
  或
  thread.submit({}, { command: { goto: END } })
  -> POST /threads/{thread_id}/runs/stream
  （同一路径，不同 body: 带 command）
```

## 3) 对话生命周期（主链）

1. 进入页面，Provider 装配完成。
2. `StreamProvider` 建立 `useStream` 会话。
3. 用户输入文本/附件，`handleSubmit` 组装 human message。
4. `stream.submit` 触发后端运行，前端按流式更新 `messages/values`。
5. `Thread` 按消息类型分发到 `HumanMessage / AssistantMessage`。
6. 若出现 interrupt，进入 HITL 视图，提交 `resume` 或 `goto: END`。
7. `onThreadId` 回写 query 并刷新历史列表。

## 4) 已实现功能清单

1. 流式对话（含 optimistic 更新）
2. 历史线程切换与状态恢复（`fetchStateHistory: true`）
3. AI 重生成（checkpoint）
4. Human 消息编辑并重提交流
5. 分支切换（branch）
6. Tool Call / Tool Result 渲染与隐藏
7. HITL 决策（approve/edit/reject + resolve）
8. Generative UI（`onCustomEvent + uiMessageReducer + LoadExternalComponent`）
9. 多模态输入（图片/PDF 上传、拖拽、粘贴）
10. 可选 Next.js API 代理接入生产环境

## 5) 场景 -> 调用映射

1. **发送消息**
   - `handleSubmit` -> `stream.submit(payload, options)`
2. **停止输出**
   - 点击 Cancel -> `stream.stop()`
3. **重生成回答**
   - AI 命令栏 -> `stream.submit(undefined, { checkpoint })`
4. **编辑用户消息**
   - HumanMessage 编辑 -> `thread.submit({messages:[newMessage]}, { checkpoint, ... })`
5. **切换历史线程**
   - ThreadHistory 点击 -> `setThreadId(...)` -> Stream 恢复历史
6. **处理中断审批**
   - HITL 视图 -> `thread.submit({command:{resume:{decisions}}})`
   - 或 `thread.submit({command:{goto: END}})`

## 6) 逻辑图（ASCII）

### 6.1 页面与状态管理图

```text
app/page.tsx
  └─ ThreadProvider
      └─ StreamProvider(useStream)
          └─ ArtifactProvider
              └─ Thread(index.tsx)
                  ├─ 输入/发送/停止
                  ├─ 消息渲染(Human/Assistant)
                  ├─ ThreadHistory
                  └─ Artifact 面板
```

### 6.2 发送与流式回包图

```text
User Input(text/files)
   -> Thread.handleSubmit
   -> stream.submit({messages, context}, options)
   -> LangGraph run/stream (SDK 封装)
   -> useStream 更新 messages/values
   -> Thread 渲染 HumanMessage/AssistantMessage
   -> (可选) onCustomEvent -> uiMessageReducer -> values.ui -> LoadExternalComponent
```

### 6.3 中断(HITL)处理图

```text
thread.interrupt 出现
   -> AssistantMessage.Interrupt
      -> AgentInbox(ThreadView) 或 GenericInterruptView
         -> 决策提交: command.resume(decisions)
         -> 或结束:  command.goto(END)
```

### 6.4 历史线程切换图

```text
ThreadHistory click
   -> setThreadId(query)
   -> useStream(threadId + fetchStateHistory=true)
   -> 自动恢复该线程历史状态
   -> Thread 重新渲染历史消息
```

## 7) 你学习这一块的建议顺序

1. 先读 `example/ui_demo/src/components/thread/index.tsx`
2. 再读 `example/ui_demo/src/providers/Stream.tsx`
3. 然后读 `example/ui_demo/src/components/thread/messages/ai.tsx`
4. 最后读 `example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx`

按这个顺序，你会先抓住主流程，再吃掉高级场景（interrupt / generative UI / branch）。

> 如果你想按“接口清单”反查业务，请继续看：`10-api-inventory-and-business-map.md`。
