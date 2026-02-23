# LangGraph SDK 学习计划（API 主线）

## 总目标

- 能独立解释并调用：`assistants`、`threads`、`runs`、`state`、`stream`。
- 能在自己的 FastAPI + 前端中可视化 LangGraph 执行步骤。
- 能把 LangSmith 的身份控制（Authentication）与访问控制（Authorization）接入到你的学习服务。

## Auth 专项总目标（本轮新增）

- 建立一条清晰边界：
  - `Authentication` 只负责“你是谁”（身份识别）。
  - `Authorization` 只负责“你能做什么”（资源访问范围）。
- 能独立实现最小认证链路：请求头 -> 身份解析 -> `identity/permissions/role/org_id`。
- 能独立实现最小授权链路：按资源动作（如 `threads.create`）做权限校验。
- 能解释并实践“owner 归属控制”：创建资源时注入 owner，并在查询时按 owner 过滤。
- 形成一份你自己的 Auth 验收清单：401、403、owner 隔离、最小权限、错误处理。

## 阶段计划

### Phase 1：认知建立（Step 1-2）

- 建立 API 对象模型：assistant -> thread -> run -> state
- 跑通 SDK 最小链路（创建线程、发起 run、读取 state）

### Phase 2：行为观察（Step 3-5）

- 掌握 stream 事件类型（messages/updates/tasks/checkpoints/debug）
- 用 FastAPI 透传流式事件
- 前端按事件类型可视化时间线

### Phase 3：总结固化（Step 6）

- 用 checklist 验收
- 形成自己的调用模板

### Phase 4：LangSmith Auth 基础（建议 2-3 天）

- Day 1（概念与最小认证）
  - 理解认证与授权边界，不混用职责。
  - 学会 `@auth.authenticate` 的最小返回结构与 401 处理。
- Day 2（资源级授权）
  - 学会 `@auth.on` 与资源级 handler（如 `threads.create`）。
  - 按 `permissions` 实现 403 拒绝与通过路径。
- Day 3（owner 隔离与回归）
  - 在资源 metadata 写入 owner。
  - 验证不同 identity 的资源隔离、过滤与拒绝语义。

## 官方学习入口（Auth）

- 主文档：`https://docs.langchain.com/langsmith/auth`
- 你的阅读重点：
  - `@auth.authenticate`（身份识别）
  - `@auth.on`（访问控制）
  - 资源归属与过滤（owner-based access）
  - API key / service account 的使用边界

## 现在就开始（Auth 第一轮）

### Task 1：身份控制最小闭环

- 输出物：一段你自己的“身份输入 -> MinimalUserDict 输出”示例。
- 通过标准：
  - 缺失或非法凭证返回 401。
  - 合法凭证能得到稳定 identity。

### Task 2：访问控制最小闭环

- 输出物：一个资源动作的授权规则（建议先做 `threads.create`）。
- 通过标准：
  - 无权限返回 403。
  - 有权限可继续执行。

### Task 3：owner 归属策略

- 输出物：你自己的 owner 写入与过滤策略说明（1 页以内）。
- 通过标准：
  - 资源创建时能写入 owner。
  - 非 owner 访问被拒绝或被过滤。

## 常见踩坑（提前规避）

- 只做身份校验，不做资源级授权（会导致越权）。
- 忘记写 owner 元数据，后续无法做资源隔离。
- 把全局规则与资源规则混在一起，导致优先级错乱。
- 错误码语义不清：认证失败应是 401，授权失败应是 403。

## 学习节奏（建议）

- 每次只做一个 Step。
- 每个 Step 完成后必须保留运行截图或日志片段。
- 没有可运行证据，视为未完成。

## 开始顺序

1. 先读 `01-step-01-api-map.md`
2. 再做 `02-step-02-sdk-minimal.md`
3. 然后按 03 -> 06 依次推进
4. 并行开启 Auth 专项：先读 `https://docs.langchain.com/langsmith/auth`，按上面的 Task 1 -> Task 3 执行
