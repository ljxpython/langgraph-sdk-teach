# 01. 线程、用户隔离与平台交互方案（问题记录 + 最佳实践）

## 问题记录

你提出的核心问题可以归纳为三件事：

1. LangGraph 有 thread，但没有平台级用户管理，前端调用链该怎么设计？
2. 如果前端不经过平台直接创建 thread，平台怎么记录 `thread_id`？
3. 平台要做用户隔离时，平台服务与 LangGraph 应该如何解耦又保持联系？

## 直接结论（先给答案）

1. **生产环境不要让浏览器直接创建 LangGraph thread**。
2. **thread 的创建与绑定必须经过“受信任服务端边界”（Platform API 或 Next.js Server Route）**。
3. 平台与 LangGraph 的关系应是：
   - 平台是“身份与权限真相源”（source of truth）
   - LangGraph 是“执行引擎”（runtime）
   - 两者通过 `thread mapping + trace id` 关联，而不是共享用户系统。

如果 thread 创建不经过平台，平台无法可靠、实时、可审计地建立用户到线程的映射；事后补录只能靠扫描或猜测，不可作为生产主路径。

## 最佳方案：双通道 + 受控 thread 映射

### 1) 架构边界

```text
Browser
  |
  | (携带平台登录态，如 JWT/Cookie)
  v
Platform Edge (FastAPI/Next.js Server)
  |- 鉴权、租户隔离、配额、审计
  |- 维护 user_id <-> platform_session_id <-> thread_id 映射
  v
LangGraph API
```

关键点：即使你使用 `langgraph-nextjs-api-passthrough`，该 passthrough 也是服务端边界，可在这里写映射逻辑，不是浏览器直连。

### 2) 调用链（推荐时序）

```text
1) 前端打开会话
Frontend -> Platform: POST /api/ai/sessions/open
Platform:
  - 校验用户身份
  - 查找是否已有会话映射
  - 若无：调用 LangGraph 创建 thread
  - 写入映射表
Platform -> Frontend: 返回 platform_session_id

2) 前端发消息
Frontend -> Platform: POST /api/ai/sessions/{platform_session_id}/messages
Platform:
  - 通过 session_id 查到 thread_id
  - 调 LangGraph runs.stream 或 runs.wait
  - 回传流式事件/最终结果

3) 观测与审计
Platform:
  - 记录 trace_id/run_id/thread_id/user_id/status/latency/cost
```

前端不需要知道真实 `thread_id`，只使用平台的 `platform_session_id`。

## 平台与 LangGraph 如何“解耦但通信”

你强调的重点是对的：两者不应该耦合在同一个用户模型或数据库里。

正确做法是：**用协议通信，不用对象耦合**。

### 通信协议层（最小集合）

- 传输协议：HTTP + SSE（同步流式）
- 可选异步：Queue（如 Redis/RabbitMQ/Kafka）
- 关联字段：
  - `platform_session_id`（平台主键）
  - `thread_id`（LangGraph 主键）
  - `trace_id`（平台调用链）
  - `run_id`（LangGraph 执行实例）

它们只通过这些 ID 联系，不共享用户表，不共享业务对象。

### 消息传递模式 A：同步（在线聊天）

```text
Frontend -> Platform API
Platform API -> LangGraph (runs.stream / runs.wait)
LangGraph -> Platform API (event/data)
Platform API -> Frontend (平台统一响应/SSE)
```

说明：

- 平台在请求头/上下文里携带 `trace_id`。
- 平台收到 LangGraph 事件后，转换成平台内部事件或直接透传到前端。
- 平台只保存关键事件，不依赖 LangGraph 内部实现细节。

### 消息传递模式 B：异步（长任务/批处理）

```text
Frontend -> Platform API (创建任务)
Platform API -> Queue (publish ai.job.requested)
Worker -> LangGraph (执行)
Worker -> Queue (publish ai.job.completed / ai.job.failed)
Platform API -> Frontend (轮询或订阅任务状态)
```

说明：

- 这里平台与 LangGraph 没有前端实时强绑定，天然解耦。
- Worker 是防腐层（anti-corruption layer）：屏蔽 LangGraph 原语给平台上层。

### 关键：什么叫“解耦”

- 不是“完全不通信”。
- 是“只通过稳定协议 + 最小 ID 关联通信”。
- 平台可以替换 LangGraph，前端和业务 API 不需要重写。

## 推荐接口边界（防止耦合回退）

- 前端只调用平台语义接口：
  - `POST /api/ai/sessions/open`
  - `POST /api/ai/sessions/{session_id}/messages`
  - `GET /api/ai/jobs/{job_id}`
- 平台内部适配 LangGraph：
  - `threads.create`
  - `runs.stream / runs.wait`
  - `threads.get_state`

这样 LangGraph API 只存在于适配层，不泄漏到前端与业务域。

## 为什么这才解耦

“解耦”不是不关联，而是“边界稳定、职责单一”：

- 平台负责：用户身份、权限、租户、审计、成本、产品语义 API。
- LangGraph 负责：Agent 执行、线程状态、工具调用、事件流。
- 联系方式：最小关联键（`thread_id`、`run_id`、`trace_id`），避免把平台用户模型塞进 LangGraph。

## 数据模型（最小可用）

建议至少三张表：

1. `ai_session_map`
   - `platform_session_id` (pk)
   - `tenant_id`
   - `user_id`
   - `thread_id`
   - `assistant_id`
   - `status` (active/archived)
   - `created_at/updated_at`

2. `ai_run_log`
   - `trace_id` (pk)
   - `platform_session_id`
   - `thread_id`
   - `run_id`
   - `event_type` (start/tool_request/tool_result/interrupt/done/error)
   - `latency_ms`
   - `token_in/token_out/cost`
   - `error_code/error_message`
   - `created_at`

3. `ai_access_policy`（可后补）
   - `tenant_id/user_id`
   - `assistant_scope`
   - `quota_limit`

## 你当前问题的直接回答

### Q1：前端不经过平台创建 thread，平台怎么记录？

答：**无法可靠记录**。可做的只是“事后同步”，但会有竞态与归属不可信问题，不建议用于生产主路径。

### Q2：平台做用户隔离，和 LangGraph 怎么交互？

答：平台先鉴权，再用映射表查 `thread_id` 调 LangGraph；LangGraph 不承担用户体系。隔离在平台层完成。

### Q3：如何解耦又联系？

答：
- 解耦：平台不复刻 LangGraph 全 API，只做产品语义接口。
- 联系：统一使用 `platform_session_id -> thread_id` 映射，并记录 `trace_id/run_id`。

## 可执行落地顺序（个人开发者）

1. 新增 `POST /api/ai/sessions/open`（平台控制 thread 创建）。
2. 前端会话页改为只持有 `platform_session_id`。
3. 将聊天消息入口统一改为平台会话接口。
4. 在平台日志中落 `trace_id/thread_id/run_id/user_id`。
5. 再按需加 RBAC、配额、成本看板。

## 反模式（避免）

- 浏览器直接调用 `POST /threads`（生产）。
- 前端同时混用 `thread_id` 与 `platform_session_id` 作为主键。
- 让 LangGraph 承担平台用户与权限模型。

## 一句话最佳方案

将 **thread 视为平台托管资源**：创建必须经过平台边界，前端只看到平台会话 ID；平台与 LangGraph 用映射键关联，用最小字段打通审计和治理。
