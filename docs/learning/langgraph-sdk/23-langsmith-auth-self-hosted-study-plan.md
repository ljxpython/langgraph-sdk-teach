# LangSmith Auth 学习规划（Self-hosted 专项）

> 适用范围：你当前这个自托管 LangGraph 学习项目（`graph_src/` + `sdk_src/`）。

## 0. 先确认项目事实（基线）

- 你是 **self-hosted**，官方默认是“无认证”，需要你自行实现认证与授权。
- 图入口在 `langgraph.json`：`agent` 和 `deepagent_demo` 已可运行。
- 运行时能力主要在 `graph_src/agent.py`，SDK 学习入口在 `sdk_src/examples/langgraph_sdk_learn.py`。
- 当前仓库未发现 `@auth.authenticate` / `@auth.on` 实现（说明 Auth 专项应从 0 到 1）。

## 1. 学习总目标（完成标准）

完成后你应具备这 6 个能力：

1. 能清楚解释 Authentication（身份）和 Authorization（权限）的边界。
2. 能实现最小认证中间件：合法凭证通过，非法凭证返回 401。
3. 能实现最小授权策略：无权限返回 403。
4. 能实现 owner 资源隔离：创建写入 owner，读取按 owner 过滤。
5. 能把 user 信息安全传给图执行上下文（用于代理代表用户调用外部能力）。
6. 能用 SDK/HTTP 用例复现实验并留存“可运行证据”。

## 2. 官方文档映射（你要读什么）

- 核心文档：`https://docs.langchain.com/langsmith/auth`
- 必读章节：
  - Core concepts
  - Authentication
  - Authorization
  - Resource-specific handlers
  - Filter operations
  - Common access patterns

## 3. 7 天学习路线（详细执行版）

### Day 1：概念落地 + 威胁建模

- 目标：把“身份失败”和“权限失败”彻底分开。
- 任务：
  - 写一页笔记：401 vs 403 的判定规则。
  - 写一页资源矩阵：threads / runs / assistants / crons 谁可读写删。
- 交付物：
  - `Auth 概念图`（建议 Mermaid）
  - `权限矩阵 v1`

### Day 2：最小认证（AuthN）

- 目标：实现 `@auth.authenticate` 最小闭环。
- 任务：
  - 约定凭证来源（`Authorization` 或 `x-api-key`）。
  - 返回最小用户结构：`identity`、`permissions`、`role`、`org_id`。
  - 统一认证失败语义：缺失/非法凭证 -> 401。
- 验收：
  - 无凭证请求必定 401。
  - 非法凭证请求必定 401。
  - 合法凭证可访问受保护端点。

### Day 3：最小授权（AuthZ）

- 目标：实现 `@auth.on` 全局策略 + owner 隔离。
- 任务：
  - 资源创建时注入 `metadata.owner = ctx.user.identity`。
  - 资源读取/搜索返回过滤器：`{"owner": ctx.user.identity}`。
  - 补充一条权限检查（例如 `threads:create`）。
- 验收：
  - A 创建的 thread，B 不可见/不可读。
  - B 无写权限时创建 thread 返回 403。

### Day 4：资源级精细授权

- 目标：从全局 handler 升级到资源级 handler。
- 任务：
  - 增加 `@auth.on.threads.create`、`@auth.on.threads.read`。
  - 增加 `@auth.on.assistants.create`（限制高权限角色）。
  - 保留全局兜底拒绝策略（未显式允许即拒绝）。
- 验收：
  - handler 优先级符合“最具体优先”。
  - 未覆盖动作走兜底 403。

### Day 5：和现有 graph + sdk 联调

- 目标：让现有学习脚本在带身份上下文时仍可运行。
- 任务：
  - 用 `sdk_src/examples/langgraph_sdk_learn.py` 跑 assistants/threads/runs 基础命令。
  - 用不同身份分别执行：创建 thread、run、读 state。
  - 验证图执行上下文可读用户信息（按官方方式读取 `langgraph_auth_user`）。
- 验收：
  - 同一命令在不同身份下返回符合策略的差异结果。
  - graph 侧能获取到当前用户身份信息（仅用于授权/审计，不泄漏敏感字段）。

### Day 6：负向测试与边界验证

- 目标：确保策略不是“看起来能用”，而是真能抗误用。
- 任务：
  - 设计 8 组负向用例：无凭证、伪造凭证、越权读、越权写、跨 owner 读、跨 owner run、错误权限声明、未覆盖动作。
  - 逐条记录预期状态码与真实状态码。
- 验收：
  - 401/403 无混淆。
  - 无一条“越权成功”。

### Day 7：固化与复盘

- 目标：形成可复用的 Auth 模板。
- 任务：
  - 产出一份“自托管 Auth 接入模板”（认证、授权、过滤、错误处理）。
  - 产出一份“上线前检查清单”（最小权限、密钥轮换、审计字段）。
- 验收：
  - 新人按文档可在 30 分钟内复现最小 Auth 闭环。

## 4. 建议的代码落点（按你仓库结构）

- 建议新增：`graph_src/auth.py`
  - 放 `Auth()`、`@auth.authenticate`、`@auth.on*`。
- 建议新增：`tests/test_auth_stage_a1_a5.py`
  - 放 401/403/owner 隔离与 handler 优先级测试。
- 建议复用：`sdk_src/examples/langgraph_sdk_learn.py`
  - 继续作为联调入口，不额外造新 CLI。

> 说明：这是学习规划，不要求你今天就完成全部编码；先按阶段推进，每天都留“命令 + 输出证据”。

## 5. 每日证据模板（必须留档）

```text
日期:
身份:
请求:
期望:
实际:
结论:
日志/截图位置:
```

## 6. 本周第一步（现在就做）

1. 完成 Day 1 两份文档（概念图 + 权限矩阵 v1）。
2. 明确 Day 2 认证输入规范（你选 Authorization 还是 x-api-key）。
3. 准备 3 个测试身份：`owner_user`、`viewer_user`、`admin_user`。

---

如果你按这份路线执行，下一轮我们就直接进入 **Day 2 实作**：我会基于你的选择（Authorization / x-api-key）给出第一版最小认证代码骨架与测试清单。
