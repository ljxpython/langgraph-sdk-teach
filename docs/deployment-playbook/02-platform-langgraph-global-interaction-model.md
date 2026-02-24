# 02. 平台与 LangGraph 全局交互模型（解耦通信版）

## 目标

- 从全局定义平台与 LangGraph 的交互面，而不是只围绕 `thread_id`。
- 保证“架构解耦 + 可通信 + 可替换 + 可治理”。

## 一句话原则

平台与 LangGraph 只通过“稳定协议 + 最小关联键”通信；不共享用户模型，不共享业务数据库，不让 LangGraph 原语泄漏到前端业务层。

## 全局交互面清单

| 交互面 | 平台职责 | LangGraph 职责 | 通信方式 | 必要关联键 |
|---|---|---|---|---|
| 身份认证 Authentication | 识别用户/租户，颁发会话 | 不管理平台用户 | HTTP Header/JWT/Cookie | `user_id`,`tenant_id` |
| 授权 Authorization | 校验用户是否可访问 assistant/资源 | 执行层按输入运行 | 同步 API 调用前校验 | `user_id`,`assistant_scope` |
| 会话管理 Session | 维护 `platform_session_id` 生命周期 | 维护 `thread_id` 状态 | `sessions/open` + `threads.create/get` | `platform_session_id`,`thread_id` |
| 消息执行 Message Run | 统一业务接口、重试与超时 | `runs.stream/wait/resume` | HTTP + SSE | `trace_id`,`run_id`,`thread_id` |
| 事件流 Event Stream | 过滤/标准化关键事件，回传前端 | 输出官方 `event/data` | SSE | `run_id`,`event_type` |
| 长任务 Async Job | 入队、状态机、补偿 | Worker 调 LangGraph 执行 | Queue + Worker | `job_id`,`trace_id`,`run_id` |
| 错误与重试 | 错误分级、幂等重试、降级 | 返回原始错误上下文 | API + DLQ（可选） | `trace_id`,`idempotency_key` |
| 观测与审计 | 记录指标与审计日志 | 提供执行元信息 | Log/Trace/Metrics | `trace_id`,`thread_id`,`run_id` |
| 成本治理 | 限流、配额、预算告警 | token 使用发生在执行层 | 统计聚合 | `tenant_id`,`model`,`cost` |
| 数据治理 | 脱敏、留存、删除策略 | 保存运行态数据 | 生命周期任务 | `tenant_id`,`retention_policy` |

## 三层解耦模型（推荐）

```text
Frontend (只认平台语义)
        |
        v
Platform API (业务语义层)
        |
        v
AI Adapter / Gateway (防腐层)
        |
        v
LangGraph Runtime
```

### 层职责

1. Platform API
- 对前端提供业务语义接口（如“生成周报”、“风险分析”）。
- 完成鉴权、授权、租户隔离、配额校验。

2. AI Adapter / Gateway
- 负责将业务请求映射为 LangGraph 原语调用。
- 负责模型路由、重试、幂等、超时、关键事件抽样。
- 是唯一可见 LangGraph SDK/API 的层。

3. LangGraph Runtime
- 只负责图执行、状态推进、工具调用和事件流输出。

## 通信契约（建议 v1）

### A. 同步聊天/交互

```text
POST /api/ai/sessions/open
POST /api/ai/sessions/{session_id}/messages
POST /api/ai/sessions/{session_id}/resume
GET  /api/ai/sessions/{session_id}/events (SSE)
```

### B. 异步任务/批处理

```text
POST /api/ai/jobs
GET  /api/ai/jobs/{job_id}
POST /api/ai/jobs/{job_id}/cancel
```

### C. 幂等与顺序

- 所有写接口支持 `Idempotency-Key`。
- 同一 `platform_session_id` 下按 `message_seq` 递增，避免并发乱序。
- 事件输出携带 `event_seq`，前端按序消费。

## 关联键策略（核心）

必须全链路存在以下键：

- `platform_session_id`：平台会话主键（前端只认它）
- `thread_id`：LangGraph 线程键（仅适配层可见）
- `run_id`：执行实例键
- `trace_id`：跨系统追踪键
- `tenant_id/user_id`：隔离与审计键

约束：任何日志、错误、告警、重试记录至少包含 `trace_id + platform_session_id`。

## 错误模型（建议）

| 类别 | 示例 | 平台响应策略 |
|---|---|---|
| 认证失败 | token 过期 | 401，前端触发登录刷新 |
| 授权失败 | 越权 assistant | 403，记录审计事件 |
| 业务参数错误 | 缺字段/非法值 | 400，返回可读错误码 |
| LangGraph 执行错误 | tool 失败/图失败 | 502/424，保留 `trace_id` |
| 超时 | run 超时 | 504，可重试或转异步 |
| 限流/配额 | 高频请求 | 429，返回重试窗口 |

## 一致性与补偿

- Session 创建采用“先平台记录草稿，再调用 LangGraph，成功后确认”的两阶段简化流程。
- 若 LangGraph 成功但平台落库失败，进入补偿队列按 `trace_id` 回补。
- 若平台成功但 LangGraph 失败，标记 session `failed_pending_retry`。

## 安全边界

- 浏览器永不持有 LangGraph 服务端密钥。
- 平台统一做输入清洗、敏感字段脱敏、审计落盘。
- 针对工具调用结果进行输出过滤（防止泄露内部路径、密钥、PII）。

## 个人开发者最小可行版本（MVP）

1. 先做同步链路：`open -> messages(stream) -> run_logs`。
2. 建立四键追踪：`platform_session_id/thread_id/run_id/trace_id`。
3. 保留最小错误分级：400/401/403/429/5xx。
4. 增加异步任务仅在出现超时和积压时启用。

## 团队扩展版（增长后）

- 引入 AI Gateway 独立部署、统一策略中心。
- 引入消息总线与 DLQ，完善补偿链路。
- 引入 OpenTelemetry，打通 trace 到日志与指标。

## 反模式清单

- 让前端直接调用 LangGraph 原语接口作为主路径。
- 平台业务接口返回 LangGraph 内部结构给前端长期依赖。
- 没有 `Idempotency-Key` 就做重试。
- 没有 `trace_id` 就做跨系统排障。

## 最终建议

把“通信”当成第一公民：先定义协议、键、错误模型、顺序与幂等，再写业务接口。这样平台和 LangGraph 可以长期解耦，但协作稳定。

## 事实依据（官方/官方示例）

1. Agent Chat UI 生产章节明确给出两种路径：
   - Quickstart: API Passthrough（服务端代理注入密钥）
   - Advanced: Custom Authentication（客户端可直连，但需自定义鉴权与访问控制）
   参考：`example/ui_demo/README.md`

2. Agent Chat UI 示例仓库已提供 Next.js passthrough 路由实现：
   参考：`example/ui_demo/src/app/api/[..._path]/route.ts`

3. LangGraph/LangSmith 官方文档说明：若不实现自定义认证处理器，服务端只看到 API Key 拥有者，无法天然按终端用户隔离；自定义认证可注入用户级上下文并做资源授权。
   参考：
   - https://docs.langchain.com/langgraph-platform/custom-auth
   - https://docs.langchain.com/langsmith/custom-auth

4. 本仓库现有服务契约采用官方 `event/data/__interrupt__` 语义并仅补 `done/error` 传输事件，这与“平台做协议层治理、执行层保持官方语义”一致。
   参考：
   - `docs/learning/langgraph-service-core/01-api-contract.md`
   - `docs/learning/langgraph-frontend-core/06-frontend-backend-contract-v1.md`
