# 01. 架构与调用链

## 目录级架构

`example/ui_demo` 的核心可以拆成 4 层：

1. App Router 壳层：`src/app/layout.tsx`、`src/app/page.tsx`
2. Provider 层：`src/providers/Thread.tsx`、`src/providers/Stream.tsx`
3. 聊天业务层：`src/components/thread/**`
4. 接入层：`src/app/api/[..._path]/route.ts`（可选代理）

## 入口到渲染的主调用链

### Step A: 页面装配

- `src/app/layout.tsx` 挂 `NuqsAdapter`，让 URL query 成为全局状态通道。
- `src/app/page.tsx` 采用固定包裹顺序：
  `ThreadProvider -> StreamProvider -> ArtifactProvider -> Thread`

这个顺序有明确语义：`StreamProvider` 内部要调用 `useThreads()`，所以 `ThreadProvider` 必须在外层。

### Step B: Stream 初始化

`src/providers/Stream.tsx` 做三件关键事：

1. 收集配置：query + env + localStorage
2. 创建 `useTypedStream = useStream<...>`
3. 处理事件：
   - `onCustomEvent`：把 UIMessage/RemoveUIMessage 归并到 `values.ui`
   - `onThreadId`：同步 query `threadId`，并延迟刷新 thread 列表

如果 `apiUrl`/`assistantId` 缺失，会先显示设置表单，而不是直接渲染聊天。

### Step C: 用户提交

`src/components/thread/index.tsx` 的 `handleSubmit`：

1. 组装 human message（文本 + 上传内容块）
2. 调 `ensureToolCallsHaveResponses()` 补齐缺失 tool response
3. 调 `stream.submit(...)`，并传入：
   - `streamMode: ["values"]`
   - `streamSubgraphs: true`
   - `streamResumable: true`
   - `optimisticValues`（先本地乐观更新）

### Step D: 渲染与分支

- 主循环按 `stream.messages` 渲染：human -> `HumanMessage`，其余 -> `AssistantMessage`。
- `AssistantMessage` 内处理：
  - Markdown 文本
  - Tool 调用与 Tool 结果
  - interrupt 视图（HITL / generic）
  - Branch 切换（`thread.setBranch`）
- `HumanMessage` 支持编辑后在父 checkpoint 上重提交流。

### Step E: 线程历史

`src/providers/Thread.tsx` 通过 SDK client 执行 `threads.search()`。

- 如果 `assistantId` 是 UUID，用 `assistant_id` 过滤
- 否则用 `graph_id` 过滤

`src/components/thread/history/index.tsx` 首次加载拉取历史，点击条目写入 `threadId` 触发回放。

## API 路由与生产通路

`src/app/api/[..._path]/route.ts` 是可选代理层。

- 配置了 `LANGGRAPH_API_URL` 时：转发到 LangGraph（可注入 `LANGSMITH_API_KEY`）
- 未配置时：返回明确错误和提示

这使项目支持两种连接模式：

1. 学习/本地：前端直接连 LangGraph
2. 生产：前端连本站 `/api`，再由 Next 路由代理
