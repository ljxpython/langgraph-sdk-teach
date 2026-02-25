# LangGraph 学习主线（唯一入口）

你只按这份文档走，其他文档当参考手册。

## 学习顺序（统一序号）

00. `00-learning-path.md`（主线）
01. `01-step-01-api-map.md`（对象模型）
02. `02-step-02-sdk-minimal.md`（最小调用链）
03. `03-runs-api-playbook.md`（Run）
04. `04-threads-api-playbook.md`（Threads）
05. `05-step-03-stream-events.md`（Streaming）
06. `06-runtime-dynamic-config-playbook.md`（动态配置）
07. `07-local-mcp-playbook.md`（MCP）
08. `08-langgraph-runtime-context-runnables-playbook.md`（Runtime Context）
09. `09-service-observer-playbook.md`（服务观测）
10. `10-step-04-fastapi-proxy.md`（服务代理）
11. `11-step-05-frontend-observer.md`（前端观察）
12. `12-step-06-review-checklist.md`（复盘清单）
13. `13-assistants-api-playbook.md`（Assistants）
14. `14-verification-matrix.md`（验收矩阵）
15. `15-study-plan.md`（学习计划）
16. `16-deepagent-todo-skills-files-playbook.md`（DeepAgent 专项）
17. `17-streaming-frontend-backend-standard.md`（Streaming 对接规范）
18. `18-streaming-stage-s2-subgraphs-join-custom.md`（Streaming S2 进阶）
19. `19-streaming-stage-s3-hitl-time-travel.md`（Streaming S3：HITL 与 Time Travel）
20. `20-deepagent-canonical-example.md`（DeepAgent 规范案例）
21. `21-execution-checklist-template.md`（执行清单模板）
22. `22-context-only-policy-and-pitfalls.md`（Context 策略与踩坑）
23. `23-langsmith-auth-self-hosted-study-plan.md`（Self-hosted Auth 详细学习规划）
24. `24-langsmith-custom-auth-hands-on.md`（Custom Auth 实操）
25. `25-supabase-oauth-e2e-playbook.md`（Supabase OAuth 端到端实战）
26. `26-context-config-runtime-flow.md`（context/config/runtime 参数流转）
27. `27-v1-v2-framework-architecture-guide.md`（v1/v2 架构路线与设计方法）

## 能力顺序（理解导图）

1. **对象模型**：assistant / thread / run / state
2. **最小调用链**：create-thread -> wait-run -> state
3. **Run 重学（官方四篇）**：background-run / same-thread / stateless-runs / cron-jobs
4. **流式执行**：stream-run + 事件分类
5. **运行时动态配置**：模型 / 提示词 / 本地 MCP
6. **run 生命周期管理**：run-create/list/get/join/cancel
7. **A/B 实验**：thread-copy 同起点对照
8. **服务集成与可观测调试**：FastAPI wait/stream/state

## 每步怎么验证（必须留证据）

当前建议进度：你已完成 `20`，下一步执行 **21（Checklist 模板 + 回归验收）**。

并行新增专项：**LangSmith Auth（身份控制 + 访问控制）**。

下一阶段官方文档（按顺序）：

1. https://docs.langchain.com/langsmith/streaming
2. https://docs.langchain.com/langsmith/add-human-in-the-loop
3. https://docs.langchain.com/langsmith/human-in-the-loop-time-travel
4. https://docs.langchain.com/langsmith/auth

## Auth 专项起步（现在开始）

### A1) 先建立边界

- 认证（Authentication）：回答“你是谁”。
- 授权（Authorization）：回答“你能访问什么”。
- 通过标准：你能用自己的话分别举 1 个失败场景（401 vs 403）。

### A2) 最小认证闭环

- 学习点：`@auth.authenticate` 返回最小用户身份结构。
- 通过标准：
  - 无效凭证 -> 401
  - 有效凭证 -> identity 稳定可识别

### A3) 最小授权闭环

- 学习点：`@auth.on` 与资源动作规则（建议先从 `threads.create` 入手）。
- 通过标准：
  - 无权限 -> 403
  - 有权限 -> 请求通过

### A4) owner 归属隔离

- 学习点：资源创建时注入 owner，读取按 owner 过滤。
- 通过标准：
  - 同 owner 可读
  - 非 owner 被拒绝或不可见

### A5) 常见错误语义校验

- 401: 认证失败（凭证缺失/无效）
- 403: 已认证但无权限
- 通过标准：接口返回语义和错误码一致，不混淆

### 1) 对象模型

- 阅读：`01-step-01-api-map.md`
- 通过标准：能口述 `assistant -> thread -> run -> state`

### 2) 最小调用链

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run --thread-id <THREAD_ID> --assistant-id agent --message "你好"
uv run python sdk_src/examples/langgraph_sdk_learn.py state --thread-id <THREAD_ID>
```

- 通过标准：拿到 `thread_id`，且 `state` 有内容

### 3) Run 重学（官方四篇）

- 阅读：`03-runs-api-playbook.md`
- 官方对应：
  - `background-run`
  - `same-thread`
  - `stateless-runs`
  - `cron-jobs`
- 通过标准：
  - 能口述四种场景的触发方式与适用边界
  - 至少跑通 background + stateless 两类命令

### 4) 流式执行

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run --thread-id <THREAD_ID> --assistant-id agent --message "你好"
```

- 通过标准：能看到 `event=...` 多类事件

### 5) 动态配置（最关键）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --context-json '{"model_provider":"kimi","system_prompt":"你是数学助教","enable_local_mcp":true,"mcp_servers":["local_math"]}'
```

- 通过标准：run 请求中的动态参数被服务端接受（推荐 context 路径）

### 6) run 生命周期

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py run-create --thread-id <THREAD_ID> --assistant-id agent --message "写3点总结"
uv run python sdk_src/examples/langgraph_sdk_learn.py run-list --thread-id <THREAD_ID> --limit 10
uv run python sdk_src/examples/langgraph_sdk_learn.py run-get --thread-id <THREAD_ID> --run-id <RUN_ID>
uv run python sdk_src/examples/langgraph_sdk_learn.py run-join --thread-id <THREAD_ID> --run-id <RUN_ID>
```

- 通过标准：能完整追踪一个 run 从创建到完成

### 7) A/B 实验

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-copy --thread-id <THREAD_ID>
```

- 通过标准：A/B 使用同起点 thread，不互相污染

### 8) 服务集成与可观测调试

- 阅读：`09-service-observer-playbook.md`
- 通过标准：能通过 FastAPI 接口跑通 `thread -> wait/stream -> state`

## 参考手册（按需查）

- Assistants：`13-assistants-api-playbook.md`
- Threads：`04-threads-api-playbook.md`
- Threads T1 自动化测试：`tests/test_threads_stage_t1.py`
- Threads T2 自动化测试：`tests/test_threads_stage_t2.py`
- Threads T3 自动化测试：`tests/test_threads_stage_t3.py`
- Threads T4 自动化测试：`tests/test_threads_stage_t4.py`
- Streaming S1 自动化测试：`tests/test_streaming_stage_s1.py`
- DeepAgent 专项：`16-deepagent-todo-skills-files-playbook.md`
- Streaming 对接规范：`17-streaming-frontend-backend-standard.md`
- Streaming S2 自动化测试：`tests/test_streaming_stage_s2.py`
- Streaming S3 自动化测试：`tests/test_streaming_stage_s3_hitl_time_travel.py`
- DeepAgent 规范案例：`20-deepagent-canonical-example.md`
- 执行清单模板：`21-execution-checklist-template.md`
- Context 策略与踩坑：`22-context-only-policy-and-pitfalls.md`
- Self-hosted Auth 详细学习规划：`23-langsmith-auth-self-hosted-study-plan.md`
- Custom Auth 实操：`24-langsmith-custom-auth-hands-on.md`
- Supabase OAuth 端到端实战：`25-supabase-oauth-e2e-playbook.md`
- 参数流转说明：`26-context-config-runtime-flow.md`
- v1/v2 架构路线：`27-v1-v2-framework-architecture-guide.md`
- Runs：`03-runs-api-playbook.md`
- 动态配置：`06-runtime-dynamic-config-playbook.md`
- 本地 MCP：`07-local-mcp-playbook.md`
- 服务集成：`09-service-observer-playbook.md`
- 服务主线（独立目录）：`../langgraph-service-core/README.md`
- 前端主线（独立目录）：`../langgraph-frontend-core/README.md`
