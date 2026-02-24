# 11. 核心接口深度说明（基于本地 8123 OpenAPI）

数据来源：`http://127.0.0.1:8123/openapi.json`（已实际拉取并核对）。

本篇只讲 `ui_demo` 强相关的 7 组接口：

1. `/info`
2. `/threads`
3. `/threads/search`
4. `/threads/{thread_id}/runs/stream`
5. `/threads/{thread_id}/runs/{run_id}/stream`
6. `/threads/{thread_id}/state`
7. `/threads/{thread_id}/history`

## 1) GET /info

- **作用**：服务信息/健康检查。
- **请求**：无 body。
- **响应**：`200 application/json`（对象）。
- **ui_demo 场景**：启动后验证 API 可达；失败则提示连接错误。
- **代码位置**：`example/ui_demo/src/providers/Stream.tsx:57`

## 2) POST /threads

- **作用**：创建线程（会话容器）。
- **请求 schema**：`ThreadCreate`
  - 常见字段：`thread_id`, `metadata`, `if_exists`, `ttl`, `supersteps`
- **响应 schema**：`Thread`
  - 常见字段：`thread_id`, `created_at`, `updated_at`, `metadata`, `status`, `values`
- **ui_demo 场景**：首次发送消息但无 `threadId` 时，SDK 会先自动创建线程再发 run。
- **触发链**：`useStream` 内部 `client.threads.create(...)`。

## 3) POST /threads/search

- **作用**：查询线程列表（历史会话面板）。
- **请求 schema**：`ThreadSearchRequest`
  - 常见字段：`metadata`, `ids`, `values`, `status`, `limit`, `offset`, `sort_by`, `sort_order`, `select`
- **响应**：`200 application/json` 数组（Thread 列表）。
- **ui_demo 场景**：左侧 Thread History 加载与刷新。
- **代码位置**：`example/ui_demo/src/providers/Thread.tsx:46`

## 4) POST /threads/{thread_id}/runs/stream

- **作用**：在线程上创建一次 run 并以 SSE 流式返回。
- **请求 schema**：`RunCreateStateful`
  - 必要核心：`assistant_id`
  - 常见字段：
    - `input`（用户输入）
    - `command`（HITL 的 resume/goto）
    - `checkpoint`（重生成/分支回放）
    - `stream_mode`, `stream_subgraphs`, `stream_resumable`
    - `context`, `config`, `metadata`
- **响应**：`200 text/event-stream`
- **ui_demo 场景（最核心）**：
  1. 普通发送消息
  2. regenerate（带 checkpoint）
  3. human edit 后重提交流
  4. interrupt 后 `command.resume`
  5. interrupt 结束 `command.goto: END`
- **代码位置**：
  - `example/ui_demo/src/components/thread/index.tsx:217`
  - `example/ui_demo/src/components/thread/index.tsx:245`
  - `example/ui_demo/src/components/thread/messages/human.tsx:56`
  - `example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:89`
  - `example/ui_demo/src/components/thread/agent-inbox/hooks/use-interrupted-actions.tsx:191`

## 5) GET /threads/{thread_id}/runs/{run_id}/stream

- **作用**：加入已经存在的 run 流（断线恢复/重连）。
- **请求参数**：
  - path: `thread_id`, `run_id`
  - header: `Last-Event-ID`
  - query: `stream_mode`, `cancel_on_disconnect`
- **响应**：`200 text/event-stream`
- **ui_demo 场景**：`streamResumable`/重连能力相关（主要由 SDK 内部处理）。

## 6) /threads/{thread_id}/state

### 6.1 GET /threads/{thread_id}/state

- **作用**：获取线程当前最新状态（latest checkpoint）。
- **请求参数**：`thread_id`（path），`subgraphs`（query）
- **响应 schema**：`ThreadState`
  - 常见字段：`values`, `next`, `tasks`, `checkpoint`, `interrupts`
- **ui_demo 场景**：`fetchStateHistory` 的某些模式下，SDK 用它快速拿最新状态。

### 6.2 POST /threads/{thread_id}/state

- **作用**：更新线程状态（非聊天主路径常用）。
- **请求 schema**：`ThreadStateUpdate`
  - 常见字段：`values`, `checkpoint`, `as_node`
- **响应 schema**：`ThreadStateUpdateResponse`（含 `checkpoint`）
- **ui_demo 场景**：默认对话 UI 不直接调用；属于进阶状态操作接口。

## 7) /threads/{thread_id}/history

### 7.1 GET /threads/{thread_id}/history

- **作用**：拉取线程历史状态（简单查询参数版）。
- **请求参数**：`thread_id`, `limit`, `before`
- **响应**：`200 application/json` 数组（ThreadState[]）

### 7.2 POST /threads/{thread_id}/history

- **作用**：拉取线程历史状态（结构化查询版）。
- **请求 schema**：`ThreadStateSearch`
  - 常见字段：`limit`, `before`, `metadata`, `checkpoint`
- **响应**：`200 application/json` 数组（ThreadState[]）
- **ui_demo 场景**：`fetchStateHistory: true` 时主要依赖这条能力恢复会话/分支历史（通过 SDK 调用）。

## 8) 场景速查（你最常用）

```text
场景A: 用户发送消息
  -> POST /threads/{thread_id}/runs/stream

场景B: 首次发送且没有 threadId
  -> POST /threads
  -> POST /threads/{thread_id}/runs/stream

场景C: 打开历史线程侧栏
  -> POST /threads/search

场景D: 切换 threadId 后恢复上下文
  -> POST /threads/{thread_id}/history (SDK 侧)
  -> (某些模式) GET /threads/{thread_id}/state

场景E: 网络抖动后继续看同一次输出
  -> GET /threads/{thread_id}/runs/{run_id}/stream

场景F: 中断审批(HITL)
  -> POST /threads/{thread_id}/runs/stream (command.resume / command.goto)
```

## 9) 对 ui_demo 的实战理解

`ui_demo` 的对话能力其实是“一个接口 + 多种 payload 语义”：

- 主接口：`POST /threads/{thread_id}/runs/stream`
- 通过 `input/command/checkpoint` 不同组合，覆盖发送、重生成、编辑回放、审批恢复、直接结束。

这就是为什么你看到它“好像都是 threads/runs”，因为这个 demo 是围绕“会话线程 + 流式执行”建模的。
