# Platform Core Multi-User Isolation Foundation

## TL;DR

> **Quick Summary**: 在 `platform-core/` 重建平台基础层，优先完成 `tenant_id + user_id` 隔离模型与统一平台入口，并复用 LangGraph 成熟能力（assistants/threads/thread-runs）进行受控透传。  
> **Deliverables**: 新平台骨架、隔离与映射模型、LangGraph 兼容透传 API（供 `platform-web/` 零代码改动接入）、治理日志与最小自动化测试。  
> **Estimated Effort**: Medium  
> **Parallel Execution**: YES - 3 waves + final verification  
> **Critical Path**: T1 -> T5 -> T8 -> T11 -> T13

---

## Context

### Original Request
基于 `docs/deployment-playbook` 重新做平台侧，在新目录搭建基础能力；核心是少造轮子，优先复用 LangGraph 成熟能力。

### Interview Summary
**Key Discussions**:
- 新目录固定为 `platform-core/`（repo root）。
- 当前阶段核心是多用户隔离设计，主键为 `tenant_id + user_id`。
- 前端不直连 LangGraph，所有请求统一走平台边界。
- 首版复用范围固定：`assistants + threads + thread-runs`（LangGraph SDK 透传）。
- 根目录 `ui-demo/` 重命名为 `platform-web/`；前端源码逻辑不改，仅配置 API 目标切到 `platform-core`。
- 测试策略：Tests-after（先实现后补自动化测试）。

**Research Findings**:
- 官方建议长期走 custom auth + routes；纯 API key 透传不满足终端用户隔离。
- passthrough 可用于快速起步，但需补平台隔离、审计、幂等与治理。

### Metis Review
**Identified Gaps (addressed)**:
- 明确禁用客户端传 `api_url`、禁用以 `thread_id` 作为鉴权依据。
- 明确跨租户/跨用户访问的拒绝策略与幂等约束。
- 明确首版不引入 UI 改造、业务语义 API、重型 RBAC 扩展。

---

## Work Objectives

### Core Objective
完成 `platform-core/` 的最小生产可用基础：统一入口、身份隔离、会话映射、受控透传、可审计。

### Concrete Deliverables
- `platform-core/` 目录与服务启动骨架
- `tenant_id + user_id + platform_session_id <-> thread_id` 映射模型
- assistants/threads/thread-runs 的 LangGraph 兼容透传端点（白名单）
- 根目录前端目录重命名：`ui-demo/` -> `platform-web/`
- run 级治理字段日志（trace/session/thread/run/status/latency）
- 自动化测试（实现后补）覆盖核心隔离与幂等路径

### Definition of Done
- [x] 平台端点可启动并通过健康检查
- [x] 未认证请求返回 401
- [x] 跨租户/跨用户访问被拒绝（固定为 404）
- [x] 同幂等键重复创建 thread 不产生重复资源
- [x] 受控透传仅允许 assistants/threads/thread-runs 指定动作
- [x] `platform-web/` 不改业务代码，仅改 API URL 配置即可完成对话
- [x] `example/` 下文件零改动
- [x] 自动化测试通过（Tests-after）

### Must Have
- 严格统一平台入口（无前端直连 LangGraph）
- 隔离主键固定为 `tenant_id + user_id`
- API 复用优先，不重写 LangGraph 原语行为

### Must NOT Have (Guardrails)
- 不接受客户端传入 `api_url` 覆盖上游目标
- 不用原始 `thread_id` 直接做授权判定
- 不修改 `example/` 下任何文件
- 不在本阶段实现业务语义 API 大扩展

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — 全部验收通过 agent 执行命令完成。

### Test Decision
- **Infrastructure exists**: NO（新目录重建）
- **Automated tests**: Tests-after
- **Framework**: pytest（FastAPI 生态）

### QA Policy
每个任务都包含 agent 可执行 QA 场景（happy-path + failure-path），并将证据写入 `.sisyphus/evidence/`。

---

## Execution Strategy

### Parallel Execution Waves

```text
Wave 1 (foundation, parallel 6):
T1 平台项目脚手架与配置基线
T2 统一配置与环境变量约束
T3 身份上下文提取中间件（tenant_id+user_id）
T4 数据模型与迁移基线（session_map/run_log/idempotency）
T5 LangGraph 客户端与上游路由白名单
T6 统一错误模型与响应结构

Wave 2 (core isolation + passthrough, parallel 6):
T7 LangGraph 兼容线程接口（threads）
T8 LangGraph 兼容运行接口（thread-runs wait/stream）
T9 threads 查询/状态接口（受控）
T10 assistants 管理接口（受控）
T11 幂等与并发保护
T12 治理日志落盘与查询最小接口

Wave 3 (hardening + tests, parallel 5):
T13 端到端隔离规则固化（跨租户/跨用户拒绝）
T14 负向输入防护（api_url/thread_id 注入拒绝）
T15 Tests-after 自动化测试补齐
T16 文档与运行手册（仅 platform-core）
T17 前端目录重命名（ui-demo -> platform-web）

Wave FINAL (parallel review 4):
F1 Plan compliance audit (oracle)
F2 Code quality review
F3 Real QA replay
F4 Scope fidelity check
```

### Dependency Matrix

- T1: blocked by none -> blocks T7,T8,T9,T10,T15
- T2: blocked by none -> blocks T3,T5,T14
- T3: blocked by T2 -> blocks T7,T8,T9,T10,T13
- T4: blocked by none -> blocks T7,T11,T12,T15
- T5: blocked by T2 -> blocks T8,T9,T10
- T6: blocked by none -> blocks T7,T8,T9,T10,T14
- T7: blocked by T1,T3,T4,T6 -> blocks T8,T11,T13
- T8: blocked by T1,T3,T5,T6,T7 -> blocks T12,T13,T15
- T9: blocked by T1,T3,T5,T6 -> blocks T15
- T10: blocked by T1,T3,T5,T6 -> blocks T15
- T11: blocked by T4,T7 -> blocks T13,T15
- T12: blocked by T4,T8 -> blocks T15
- T13: blocked by T3,T7,T8,T11 -> blocks T15,T16,T17
- T14: blocked by T2,T6 -> blocks T15
- T15: blocked by T1,T4,T8,T9,T10,T11,T12,T13,T14 -> blocks F1-F4
- T16: blocked by T13 -> blocks F1,F4
- T17: blocked by T13 -> blocks F1,F4

### Agent Dispatch Summary

- Wave1: T1/T2/T6 -> quick, T3/T4/T5 -> unspecified-high
- Wave2: T7/T8/T11 -> deep, T9/T10/T12 -> unspecified-high
- Wave3: T13 -> deep, T14 -> unspecified-high, T15 -> deep, T16 -> writing, T17 -> quick
- Final: F1 -> oracle, F2 -> unspecified-high, F3 -> unspecified-high, F4 -> deep

---

## TODOs

- [x] 1. 初始化 `platform-core/` 服务骨架

  **What to do**:
  - 创建 `platform-core/` 最小目录：`app/`、`tests/`、`alembic/`、基础启动入口。
  - 配置可启动 FastAPI 应用与 `/healthz`。

  **Must NOT do**:
  - 不引入业务语义 API。
  - 不修改 `example/` 下任何源码。

  **Recommended Agent Profile**:
  - **Category**: `quick`（骨架初始化）
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（当前非 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2,T3,T4,T5,T6)
  - **Blocks**: T7,T8,T9,T10,T15
  - **Blocked By**: None

  **References**:
  - `docs/deployment-playbook/README.md` - 平台最小生产架构基线。
  - `docs/deployment-playbook/02-platform-langgraph-global-interaction-model.md` - 三层交互模型与边界。

  **Acceptance Criteria**:
  - [ ] `uv run uvicorn platform_core.app.main:app --port 8011` 可启动。
  - [ ] `curl -i http://127.0.0.1:8011/healthz` 返回 200。

  **QA Scenarios**:
  ```text
  Scenario: 健康检查成功
    Tool: Bash (curl)
    Preconditions: 服务已启动在 8011
    Steps:
      1. 执行 `curl -s -o /tmp/t1.txt -w "%{http_code}" http://127.0.0.1:8011/healthz`
      2. 断言状态码等于 `200`
      3. 保存响应到 `.sisyphus/evidence/task-1-healthz-ok.txt`
    Expected Result: 返回 200，响应体包含健康状态字段
    Failure Indicators: 状态码非 200 或连接失败
    Evidence: .sisyphus/evidence/task-1-healthz-ok.txt

  Scenario: 未定义路由拒绝
    Tool: Bash (curl)
    Preconditions: 服务已启动在 8011
    Steps:
      1. 执行 `curl -s -o /tmp/t1-404.txt -w "%{http_code}" http://127.0.0.1:8011/not-found`
      2. 断言状态码为 `404`
    Expected Result: 返回 404
    Evidence: .sisyphus/evidence/task-1-not-found-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): bootstrap minimal service skeleton`

- [x] 2. 统一配置与环境变量约束

  **What to do**:
  - 定义配置模块（上游 URL、超时、白名单、数据库 DSN、日志级别）。
  - 严格禁止请求体级 `api_url` 覆盖。

  **Must NOT do**:
  - 不允许动态切换任意上游地址。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（无前端）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T3,T5,T14
  - **Blocked By**: None

  **References**:
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - 透传分层与治理定位。
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 平台边界统一入口原则。

  **Acceptance Criteria**:
  - [ ] 配置仅接受服务端环境变量，不接受请求覆盖上游目标。
  - [ ] 非法配置启动即失败（fail-fast）。

  **QA Scenarios**:
  ```text
  Scenario: 合法配置启动
    Tool: Bash
    Preconditions: 设置必需环境变量
    Steps:
      1. 启动服务并检查进程退出码为 0
      2. 请求 `/healthz` 返回 200
    Expected Result: 服务成功启动
    Evidence: .sisyphus/evidence/task-2-config-valid.txt

  Scenario: 缺失关键配置失败
    Tool: Bash
    Preconditions: 清除关键上游环境变量
    Steps:
      1. 启动服务
      2. 断言进程非 0 退出且报配置错误
    Expected Result: fail-fast
    Evidence: .sisyphus/evidence/task-2-config-invalid-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add strict server-side config constraints`

- [x] 3. 身份上下文中间件（`tenant_id + user_id`）

  **What to do**:
  - 从认证上下文提取并注入 `tenant_id`、`user_id`。
  - 禁止从 body/query/header 伪造身份字段。

  **Must NOT do**:
  - 不信任客户端传入的身份键值。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `git-master`（非 git 操作）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7,T8,T9,T10,T13
  - **Blocked By**: T2

  **References**:
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 用户与线程映射主路径。
  - `https://docs.langchain.com/langgraph-platform/custom-auth` - 用户身份传播与隔离原因。

  **Acceptance Criteria**:
  - [ ] 无认证上下文返回 401。
  - [ ] 认证上下文可在后续 handler 读取 `tenant_id/user_id`。

  **QA Scenarios**:
  ```text
  Scenario: 认证上下文注入成功
    Tool: Bash (curl)
    Preconditions: 使用有效测试 token `Bearer tenantA_user1`
    Steps:
      1. 调用受保护接口
      2. 断言返回 200 且服务日志含 `tenant_id=tenantA user_id=user1`
    Expected Result: 身份上下文可用
    Evidence: .sisyphus/evidence/task-3-auth-context-ok.txt

  Scenario: 伪造身份字段被忽略/拒绝
    Tool: Bash (curl)
    Preconditions: 请求体携带 `tenant_id=evil`
    Steps:
      1. 调用同一接口
      2. 断言服务仍按 token 身份执行，或直接 400 拒绝
    Expected Result: 客户端身份注入无效
    Evidence: .sisyphus/evidence/task-3-auth-context-injection-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): enforce tenant-user identity context`

- [x] 4. 数据模型与迁移基线

  **What to do**:
  - 建立 `session_map`、`run_log`、`idempotency` 三类核心表。
  - 给 `tenant_id + user_id + assistant_id` 建唯一性/索引策略。

  **Must NOT do**:
  - 不引入非核心业务表。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（非 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7,T11,T12,T15
  - **Blocked By**: None

  **References**:
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 建议的数据模型字段。
  - `docs/deployment-playbook/04-postgres-vs-mysql-vs-sqlite.md` - 数据库与迁移基线。

  **Acceptance Criteria**:
  - [ ] 迁移可执行且可回滚。
  - [ ] 唯一约束能阻止重复会话映射。

  **QA Scenarios**:
  ```text
  Scenario: 迁移执行成功
    Tool: Bash
    Preconditions: 数据库可连接
    Steps:
      1. 执行迁移命令
      2. 查询表结构确认 3 张核心表存在
    Expected Result: migration success
    Evidence: .sisyphus/evidence/task-4-migration-ok.txt

  Scenario: 重复会话写入被约束拦截
    Tool: Bash
    Preconditions: 插入相同 `(tenant_id,user_id,assistant_id)` 两次
    Steps:
      1. 第二次插入执行
      2. 断言返回唯一约束冲突
    Expected Result: duplicate blocked
    Evidence: .sisyphus/evidence/task-4-unique-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add isolation mapping schema and migrations`

- [x] 5. LangGraph 客户端与端点白名单

  **What to do**:
  - 封装 LangGraph SDK 客户端创建与超时策略。
  - 固定允许动作：assistants、threads、thread-runs；拒绝其他透传目标。

  **Must NOT do**:
  - 不做任意路径泛透传。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `writing`（非文档主任务）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T8,T9,T10
  - **Blocked By**: T2

  **References**:
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - 可管理能力矩阵。
  - `https://docs.langchain.com/langsmith/server-api-ref` - 默认端点能力参考。

  **Acceptance Criteria**:
  - [ ] 白名单内动作可达。
  - [ ] 非白名单动作固定返回 403。

  **QA Scenarios**:
  ```text
  Scenario: 白名单内调用成功
    Tool: Bash (curl)
    Preconditions: 服务已启动，鉴权有效
    Steps:
      1. 调用 assistants/threads 合法透传接口
      2. 断言返回 200
    Expected Result: allowed endpoint success
    Evidence: .sisyphus/evidence/task-5-whitelist-ok.txt

  Scenario: 非白名单路径被拒绝
    Tool: Bash (curl)
    Preconditions: 服务已启动
    Steps:
      1. 调用未允许路径（如 store/任意路径）
      2. 断言返回 403
    Expected Result: blocked endpoint
    Evidence: .sisyphus/evidence/task-5-whitelist-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add controlled LangGraph endpoint allowlist`

- [x] 6. 统一错误模型与响应结构

  **What to do**:
  - 定义统一错误码与结构（认证、授权、参数、上游失败、超时）。
  - 统一响应中附带 `trace_id`。

  **Must NOT do**:
  - 不直接透出上游内部堆栈。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（非 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7,T8,T9,T10,T14
  - **Blocked By**: None

  **References**:
  - `docs/deployment-playbook/02-platform-langgraph-global-interaction-model.md` - 错误模型建议。
  - `docs/deployment-playbook/README.md` - 最小治理字段要求。

  **Acceptance Criteria**:
  - [ ] 所有失败响应含统一错误结构。
  - [ ] 每个响应头或响应体含 `trace_id`。

  **QA Scenarios**:
  ```text
  Scenario: 参数错误返回统一结构
    Tool: Bash (curl)
    Preconditions: 服务已启动
    Steps:
      1. 调用接口并故意缺字段
      2. 断言 400 且 JSON 包含 `code`,`message`,`trace_id`
    Expected Result: standardized error payload
    Evidence: .sisyphus/evidence/task-6-error-shape-ok.json

  Scenario: 上游失败不泄露内部细节
    Tool: Bash (curl)
    Preconditions: 模拟上游不可达
    Steps:
      1. 调用受影响接口
      2. 断言返回 5xx 且无内部堆栈文本
    Expected Result: sanitized upstream error
    Evidence: .sisyphus/evidence/task-6-upstream-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): standardize error model with trace id`

- [x] 7. LangGraph 兼容线程接口（`/threads`）

  **What to do**:
  - 提供与 `ui-demo/`（重命名后 `platform-web/`）主链兼容的线程接口（create/search/get 等实际被调用子集）。
  - 在兼容层内部完成 `tenant_id + user_id` 到 thread 归属校验与映射。

  **Must NOT do**:
  - 不让客户端凭原始 `thread_id` 越权读取他人线程。

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `writing`（非文档主任务）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential in Wave 2
  - **Blocks**: T8,T11,T13
  - **Blocked By**: T1,T3,T4,T6

  **References**:
  - `ui-demo/src/app/api/[..._path]/route.ts` - 前端当前调用形态（LangGraph 风格路径）。
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - threads 能力子集建议。

  **Acceptance Criteria**:
  - [ ] `POST /threads`、`POST /threads/search` 等 `ui-demo/` 必需路径可用。
  - [ ] 返回结构与 LangGraph SDK 调用预期兼容。

  **QA Scenarios**:
  ```text
  Scenario: 线程创建兼容调用成功
    Tool: Bash (curl)
    Preconditions: `Authorization: Bearer tenantA_user1`
    Steps:
      1. 调用 `POST /threads`，body: `{}`
      2. 断言 200 且响应含 `thread_id`
    Expected Result: `ui-demo/` 兼容线程创建成功
    Evidence: .sisyphus/evidence/task-7-threads-create-ok.json

  Scenario: 跨用户线程读取失败
    Tool: Bash (curl)
    Preconditions: 使用 user2 token 读取 user1 thread
    Steps:
      1. 调用 `GET /threads/{thread_id}`
      2. 断言返回 404
    Expected Result: ownership isolation enforced
    Evidence: .sisyphus/evidence/task-7-threads-read-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add langgraph-compatible thread endpoints`

- [x] 8. LangGraph 兼容运行接口（`/threads/{thread_id}/runs/*`）

  **What to do**:
  - 提供 `ui-demo/` 对话主链所需 runs 接口（wait/stream/join 依实际调用面）。
  - 在兼容层对 `thread_id` 执行归属校验后再调用上游 run。

  **Must NOT do**:
  - 不绕过归属校验直接向上游发 run。

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（无 UI 操作）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential in Wave 2
  - **Blocks**: T12,T13,T15
  - **Blocked By**: T1,T3,T5,T6,T7

  **References**:
  - `ui-demo/README.md` - 当前前端生产接入路径与调用方式。
  - `docs/learning/langgraph-service-core/01-api-contract.md` - event/data 兼容要求。

  **Acceptance Criteria**:
  - [ ] `POST /threads/{thread_id}/runs/*` 主链调用成功并返回 `run_id`。
  - [ ] stream 输出可被现有 `ui-demo/` 消费（无需改 UI 代码）。

  **QA Scenarios**:
  ```text
  Scenario: run 兼容调用 happy path
    Tool: Bash (curl)
    Preconditions: 已有有效 `thread_id`
    Steps:
      1. 调用 `POST /threads/{thread_id}/runs/wait`，message=`"hello"`
      2. 断言响应含 `run_id`,`trace_id`
    Expected Result: run created and completed
    Evidence: .sisyphus/evidence/task-8-runs-wait-ok.json

  Scenario: 非归属 thread run 被拒绝
    Tool: Bash (curl)
    Preconditions: 使用非归属用户 token 调用同一 thread
    Steps:
      1. 调用 `POST /threads/{thread_id}/runs/wait`
      2. 断言返回 404
    Expected Result: unauthorized ownership blocked
    Evidence: .sisyphus/evidence/task-8-runs-wait-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add langgraph-compatible run endpoints`

- [x] 9. threads 查询与状态接口（受控）

  **What to do**:
  - 提供受控 threads 查询/状态读取接口。
  - 所有读取必须基于 `tenant_id + user_id + thread ownership` 过滤。

  **Must NOT do**:
  - 不提供跨身份的任意 thread 读取。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（后端任务）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T10,T11,T12)
  - **Blocks**: T15
  - **Blocked By**: T1,T3,T5,T6

  **References**:
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - threads 能力边界。
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 映射查询原则。

  **Acceptance Criteria**:
  - [ ] 合法身份能读取本人的线程状态。
  - [ ] 跨用户/跨租户读取返回拒绝。

  **QA Scenarios**:
  ```text
  Scenario: 本人线程状态查询成功
    Tool: Bash (curl)
    Preconditions: tenantA/user1 有有效 session
    Steps:
      1. 调用线程状态查询接口
      2. 断言返回 200 且 thread_id 匹配映射
    Expected Result: own thread visible
    Evidence: .sisyphus/evidence/task-9-thread-state-ok.json

  Scenario: 跨用户查询失败
    Tool: Bash (curl)
    Preconditions: 使用 tenantA/user2 token 查询 user1 session
    Steps:
      1. 调用同一路径
      2. 断言返回 404
    Expected Result: cross-user blocked
    Evidence: .sisyphus/evidence/task-9-thread-state-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add constrained thread query endpoints`

- [x] 10. assistants 管理接口（受控复用）

  **What to do**:
  - 暴露首版需要的 assistants 列表/读取/必要管理动作。
  - 对动作范围做白名单约束并记录审计字段。

  **Must NOT do**:
  - 不开放无边界 assistants 全量管理。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（无前端）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T15
  - **Blocked By**: T1,T3,T5,T6

  **References**:
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - assistants 可管理能力矩阵。
  - `docs/deployment-playbook/README.md` - 不重复造轮子原则。

  **Acceptance Criteria**:
  - [ ] assistants 合法动作可执行。
  - [ ] 未授权动作返回拒绝并带 trace_id。

  **QA Scenarios**:
  ```text
  Scenario: assistants 列表读取成功
    Tool: Bash (curl)
    Preconditions: 有效 token
    Steps:
      1. 调用 assistants list
      2. 断言返回 200 且数组结构正确
    Expected Result: assistant list available
    Evidence: .sisyphus/evidence/task-10-assistants-list-ok.json

  Scenario: 未允许动作被拒绝
    Tool: Bash (curl)
    Preconditions: 调用未开放动作
    Steps:
      1. 请求该动作
      2. 断言 403 且响应含 trace_id
    Expected Result: action blocked
    Evidence: .sisyphus/evidence/task-10-assistants-action-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add controlled assistants passthrough`

- [x] 11. 幂等与并发保护

  **What to do**:
  - 为线程创建与关键写操作加入 `Idempotency-Key`。
  - 增加并发冲突保护，避免重复 session/run。

  **Must NOT do**:
  - 不依赖“客户端不重试”假设。

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `writing`（非文档主任务）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T13,T15
  - **Blocked By**: T4,T7

  **References**:
  - `docs/deployment-playbook/02-platform-langgraph-global-interaction-model.md` - 幂等与顺序建议。
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 会话映射一致性要求。

  **Acceptance Criteria**:
  - [ ] 同 key 重复请求返回同一结果。
  - [ ] 并发创建不产生重复映射。

  **QA Scenarios**:
  ```text
  Scenario: 幂等键重复请求返回同一 thread
    Tool: Bash
    Preconditions: 同一 token、相同 Idempotency-Key
    Steps:
      1. 连续调用 `POST /threads` 两次
      2. 断言两次 `thread_id` 相同
    Expected Result: idempotent success
    Evidence: .sisyphus/evidence/task-11-idempotency-ok.txt

  Scenario: 并发创建不会重复
    Tool: Bash
    Preconditions: 并发触发 `POST /threads`（至少 2 并发）
    Steps:
      1. 并行请求创建线程
      2. 断言最终仅一条映射记录
    Expected Result: no duplicate session mapping
    Evidence: .sisyphus/evidence/task-11-concurrency-errorcheck.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): enforce idempotency and concurrency safety`

- [x] 12. 治理日志落盘与查询最小接口

  **What to do**:
  - 记录 `trace_id,tenant_id,user_id,platform_session_id,thread_id,run_id,status,latency`。
  - 提供最小查询接口支持按 session/run 回溯。

  **Must NOT do**:
  - 不记录敏感明文凭据。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（非 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T15
  - **Blocked By**: T4,T8

  **References**:
  - `docs/deployment-playbook/README.md` - 最小治理字段清单。
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - run 日志模型建议。

  **Acceptance Criteria**:
  - [ ] 每次 run 都有完整治理字段日志。
  - [ ] 查询接口能按 session/run 返回结果。

  **QA Scenarios**:
  ```text
  Scenario: run 日志字段完整
    Tool: Bash
    Preconditions: 至少执行一次 messages 接口
    Steps:
      1. 查询日志记录
      2. 断言关键字段均非空
    Expected Result: governance fields complete
    Evidence: .sisyphus/evidence/task-12-log-fields-ok.json

  Scenario: 非法查询参数被拒绝
    Tool: Bash (curl)
    Preconditions: 传入无效 run_id 格式
    Steps:
      1. 调用日志查询接口
      2. 断言 400 且错误结构标准化
    Expected Result: invalid query rejected
    Evidence: .sisyphus/evidence/task-12-log-query-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): add run governance logging and lookup`

- [x] 13. 跨租户/跨用户隔离规则固化

  **What to do**:
  - 固化访问判定：资源访问必须匹配 `tenant_id + user_id`。
  - 统一拒绝语义（固定 404）并全接口一致。

  **Must NOT do**:
  - 不出现身份隔离拒绝码不一致行为。

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（后端任务）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with T14,T15,T16)
  - **Blocks**: T15,T16
  - **Blocked By**: T3,T7,T8,T11

  **References**:
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 隔离与映射策略。
  - `https://docs.langchain.com/langgraph-platform/custom-auth` - 用户级访问控制动机。

  **Acceptance Criteria**:
  - [ ] 跨用户访问同租户资源被拒绝。
  - [ ] 跨租户访问被拒绝。

  **QA Scenarios**:
  ```text
  Scenario: 同租户不同用户访问被拒绝
    Tool: Bash (curl)
    Preconditions: user1 已创建 session，使用 user2 token
    Steps:
      1. 调用 `POST /threads/{thread_id}/runs/wait`
      2. 断言返回固定拒绝码
    Expected Result: cross-user blocked
    Evidence: .sisyphus/evidence/task-13-cross-user-error.txt

  Scenario: 跨租户访问被拒绝
    Tool: Bash (curl)
    Preconditions: tenantA session，使用 tenantB token
    Steps:
      1. 调用同一路径
      2. 断言返回固定拒绝码
    Expected Result: cross-tenant blocked
    Evidence: .sisyphus/evidence/task-13-cross-tenant-error.txt
  ```

  **Commit**: YES
  - Message: `feat(platform-core): harden tenant-user isolation policy`

- [x] 14. 负向输入防护（注入与越权）

  **What to do**:
  - 拒绝 `api_url`、原始 `thread_id` 等越权输入。
  - 对关键输入加白名单校验与结构校验。

  **Must NOT do**:
  - 不把危险字段“静默透传”给上游。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（无 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T15
  - **Blocked By**: T2,T6

  **References**:
  - Metis gap review结论（本计划 Context 小节）- 禁止 caller `api_url` 覆盖。
  - `docs/deployment-playbook/02-platform-langgraph-global-interaction-model.md` - 安全边界要求。

  **Acceptance Criteria**:
  - [ ] 输入含 `api_url` 时返回 400。
  - [ ] 输入含非法 `thread_id` 注入字段时返回 400。

  **QA Scenarios**:
  ```text
  Scenario: api_url 注入被拒绝
    Tool: Bash (curl)
    Preconditions: 有效 token
    Steps:
      1. 调用 messages 接口，body 包含 `"api_url":"http://evil"`
      2. 断言 400
    Expected Result: override blocked
    Evidence: .sisyphus/evidence/task-14-api-url-injection-error.txt

  Scenario: thread_id 注入被拒绝
    Tool: Bash (curl)
    Preconditions: 有效 token
    Steps:
      1. 调用 messages 接口，body 强行传 `thread_id`
      2. 断言返回拒绝码
    Expected Result: thread injection blocked
    Evidence: .sisyphus/evidence/task-14-thread-injection-error.txt
  ```

  **Commit**: YES
  - Message: `fix(platform-core): block unsafe override and injection inputs`

- [x] 15. Tests-after 自动化测试补齐

  **What to do**:
  - 为 T7-T14 增加自动化测试：认证、隔离、幂等、白名单、错误模型。
  - 引入最小测试夹具与假数据。

  **Must NOT do**:
  - 不只做 happy-path。

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `writing`（非文档主任务）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential in Wave 3
  - **Blocks**: F1,F2,F3,F4
  - **Blocked By**: T1,T4,T8,T9,T10,T11,T12,T13,T14

  **References**:
  - `docs/deployment-playbook/01-thread-identity-isolation-playbook.md` - 隔离验收目标。
  - `docs/deployment-playbook/02-platform-langgraph-global-interaction-model.md` - 幂等/顺序/错误模型。

  **Acceptance Criteria**:
  - [ ] 测试覆盖核心路径与失败路径。
  - [ ] `pytest` 全绿通过。

  **QA Scenarios**:
  ```text
  Scenario: 自动化测试全通过
    Tool: Bash
    Preconditions: 测试依赖安装完成
    Steps:
      1. 执行 `uv run pytest platform-core/tests -q`
      2. 断言退出码 0
    Expected Result: all tests pass
    Evidence: .sisyphus/evidence/task-15-pytest-ok.txt

  Scenario: 关键隔离用例可触发失败
    Tool: Bash
    Preconditions: 临时注入错误配置或 mock 破坏隔离判定
    Steps:
      1. 运行指定隔离测试
      2. 断言测试失败可检测到回归
    Expected Result: regression detectable
    Evidence: .sisyphus/evidence/task-15-isolation-regression-error.txt
  ```

  **Commit**: YES
  - Message: `test(platform-core): add isolation and passthrough test coverage`

- [x] 16. `platform-core` 运维与开发手册

  **What to do**:
  - 编写 `platform-core/README.md`：启动、配置、接口范围、边界与反模式。
  - 明确“`platform-web/` 零代码改动接入”方式（仅配置 API URL）。

  **Must NOT do**:
  - 不在文档里承诺本阶段未交付能力。

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `playwright`（非 UI）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: F1,F4
  - **Blocked By**: T13

  **References**:
  - `docs/deployment-playbook/README.md` - 总体模式说明。
  - `docs/deployment-playbook/03-manageable-capabilities-via-passthrough.md` - 透传控制强度分级。

  **Acceptance Criteria**:
  - [ ] 文档包含启动命令、环境变量、受控 API 列表。
  - [ ] 文档明确 `platform-web/` 无需改码，仅配置接入方式。

  **QA Scenarios**:
  ```text
  Scenario: 按文档冷启动成功
    Tool: Bash
    Preconditions: 清洁环境
    Steps:
      1. 严格按 README 执行启动步骤
      2. 调用 `/healthz` 断言 200
    Expected Result: docs are executable
    Evidence: .sisyphus/evidence/task-16-readme-run-ok.txt

  Scenario: 文档范围检查
    Tool: Bash
    Preconditions: README 已生成
    Steps:
      1. 检查 README 含 “Compatibility with platform-web” 小节
      2. 检查明确“无需改 `platform-web/` 业务代码，仅改 API URL 配置”
    Expected Result: scope boundaries explicit
    Evidence: .sisyphus/evidence/task-16-readme-scope-check.txt
  ```

  **Commit**: YES
  - Message: `docs(platform-core): add phase-1 runbook and boundaries`

- [x] 17. 前端目录重命名（`ui-demo/` -> `platform-web/`）

  **What to do**:
  - 将仓库根目录 `ui-demo/` 重命名为 `platform-web/`。
  - 同步更新仅路径级引用（脚本、README、运行命令中的目录名）。

  **Must NOT do**:
  - 不修改 `example/` 下任何文件。
  - 不改动 `platform-web/` 内业务实现逻辑。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: `[]`
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（本任务仅重命名与路径同步）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: F1,F4
  - **Blocked By**: T13

  **References**:
  - `ui-demo/README.md` - 当前前端入口与启动文档。
  - `README.md` - 仓库级目录引用检查点。

  **Acceptance Criteria**:
  - [ ] 仓库根目录存在 `platform-web/` 且不再存在 `ui-demo/`。
  - [ ] `example/` 目录 diff 为 0。

  **QA Scenarios**:
  ```text
  Scenario: 重命名后前端可启动
    Tool: Bash
    Preconditions: 完成目录重命名
    Steps:
      1. 在 `platform-web/` 执行既有启动命令
      2. 断言启动成功并可访问本地页面
    Expected Result: rename does not break startup
    Evidence: .sisyphus/evidence/task-17-rename-startup-ok.txt

  Scenario: example 目录未被改动
    Tool: Bash
    Preconditions: 完成本任务所有改动
    Steps:
      1. 执行 `git diff --name-only -- example/`
      2. 断言输出为空
    Expected Result: no changes under example/
    Evidence: .sisyphus/evidence/task-17-example-unchanged-ok.txt
  ```

  **Commit**: YES
  - Message: `chore(repo): rename ui-demo to platform-web`

---

## Final Verification Wave (MANDATORY)

- [x] F1. **Plan Compliance Audit** — `oracle`
  - 按 Must Have / Must NOT Have 全量核对实现与证据文件。
  - 输出：`Must Have [N/N] | Must NOT Have [N/N] | VERDICT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  - 执行类型检查、lint、测试，排查脆弱实现与无效分支。
  - 输出：`Build/Lint/Tests | VERDICT`

- [x] F3. **Real QA Replay** — `unspecified-high`
  - 执行所有任务 QA 场景并核验证据文件。
  - 输出：`Scenarios [N/N] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  - 核对任务边界，检查越界实现与遗漏。
  - 输出：`Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

- `feat(platform-core): bootstrap multi-user isolation foundation`
- `feat(platform-core): add controlled LangGraph passthrough endpoints`
- `test(platform-core): add isolation and idempotency coverage`
- `docs(platform-core): add operational runbook`
- `chore(repo): rename ui-demo to platform-web`

---

## Success Criteria

### Verification Commands

```bash
uv run uvicorn platform_core.app.main:app --port 8011
uv run pytest platform-core/tests -q
curl -i -X POST http://127.0.0.1:8011/threads
```

### Final Checklist

- [x] 所有 Must Have 满足
- [x] 所有 Must NOT Have 满足
- [x] 自动化测试通过
- [x] 证据文件齐全
