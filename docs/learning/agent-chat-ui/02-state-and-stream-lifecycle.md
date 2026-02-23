# 02. 状态与流式生命周期

## 1) 状态来源（Source of Truth）

这个项目不是单一状态源，而是“分层状态源”：

1. URL Query（`nuqs`）
   - `apiUrl`, `assistantId`, `threadId`, `chatHistoryOpen`, `hideToolCalls`
2. localStorage
   - `lg:chat:apiKey`
3. env
   - `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ASSISTANT_ID`
4. 运行态（`useStream`）
   - `messages`, `values`, `isLoading`, `error`, `interrupt`

理解这个分层非常关键：query 决定“当前会话上下文”，stream 决定“当前执行态”。

## 2) 提交生命周期（submit -> stream -> render）

### 2.1 submit 前

`src/components/thread/index.tsx`：

- 输入文本 + 上传文件块合成一个 `human` message
- `ensureToolCallsHaveResponses(messages)` 会在必要时补 `tool` 消息，避免工具调用链断裂

### 2.2 submit 过程

调用 `stream.submit(payload, options)`，关键 options：

- `streamMode: ["values"]`：以 values 流更新 UI
- `streamSubgraphs: true`：包含子图执行流
- `streamResumable: true`：允许运行中断后继续
- `optimisticValues`：本地立即先显示，降低等待感

### 2.3 stream 消费

`useStream` 持续更新 `messages` 与 `values`，组件层自动重渲染：

- `Thread` 负责列表渲染和 loading 占位
- `AssistantMessage` 负责 AI 文本 / 工具卡片 / interrupt
- `HumanMessage` 负责编辑重提交流

## 3) 自定义 UI 事件生命周期（Generative UI）

`src/providers/Stream.tsx` 的 `onCustomEvent`：

- 识别 `UIMessage` / `RemoveUIMessage`
- 用 `uiMessageReducer` 写入 `prev.ui`

`src/components/thread/messages/ai.tsx` 的 `CustomComponent`：

- 从 `values.ui` 过滤 `metadata.message_id === 当前消息`
- 用 `LoadExternalComponent` 渲染动态 UI

这就是“后端推 UI，前端装配渲染”的主链。

## 4) 线程生命周期

### 4.1 threadId 生成与同步

`onThreadId` 回调拿到后端 threadId 后：

1. 写入 query `threadId`
2. 延迟后刷新 thread list（让新 thread 能被检索到）

### 4.2 历史线程切换

`ThreadHistory` 点击条目后写 query `threadId`。
`useStream(fetchStateHistory: true)` 会按 thread 上下文恢复历史状态。

## 5) 分支与重跑生命周期

1. 分支切换：`thread.setBranch(branch)`
2. regenerate：带 `checkpoint` 调 `submit(undefined, {...})`
3. human message edit：在父 checkpoint 上提交新的 human 内容

这三条都依赖 `getMessagesMetadata(message)` 返回的 metadata。

## 6) 中断（HITL）生命周期

路径：

1. `thread.interrupt` 出现
2. `isAgentInboxInterruptSchema` 判定是否是 Agent Inbox 结构
3. 命中则走 `ThreadView`（带 approve/edit/reject UI）
4. 最终通过 command 提交：
   - `resume: { decisions }`
   - 或 `goto: END`（标记 resolved）

支持多 action 批量决策（`thread-actions-view.tsx`）。

## 7) 多模态输入生命周期（图片/PDF）

`use-file-upload.tsx` 统一处理三类输入：

- 文件选择
- 拖拽
- 粘贴

流转：

1. 类型校验（JPEG/PNG/GIF/WEBP/PDF）
2. 去重校验（同一消息内禁止重复）
3. `fileToContentBlock` 转 base64 内容块
4. 与文本一并进入 message content
