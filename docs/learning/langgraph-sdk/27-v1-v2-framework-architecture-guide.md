# LangGraph 开发框架设计指南（v1 Factory vs v2 Graph-Native）

## 1. 先给结论

- 你当前两条路线的理解是对的：
  - **v1**：Agent Server factory 路线（`make_graph(config, runtime)` + `ServerRuntime`）
  - **v2**：Pure graph-native 路线（compiled `graph` + `context_schema` + `Runtime[Context]`）
- 两条都符合官方能力边界；不是“谁对谁错”，而是阶段目标不同。
- 当前仓的演进策略：**默认 v2 主线**（pure graph-native）。
- v1 保留为边界适配层：仅在需要 `ServerRuntime` 控制面能力时使用。

---

## 2. 两条路线到底是什么

### 2.1 v1：Agent Server factory 路线

形态：

- `langgraph.json` 指向工厂函数（例如 `...:make_graph`）
- 工厂签名使用 `ServerRuntime[Context]`
- 在工厂里按本次 run 动态装配模型、MCP、tools、skills

适用：

- 需要按请求动态装配依赖（比如仅执行态才连接 MCP）
- 需要使用 server 访问上下文（user/store/access_context）

当前仓示例：`graph_src_v1`

### 2.2 v2：Pure graph-native 路线

形态：

- `langgraph.json` 指向 compiled graph（例如 `.../graph.py:graph`）
- `StateGraph(..., context_schema=RuntimeContext)`
- 节点签名读取 `runtime: Runtime[RuntimeContext]`

适用：

- 希望图定义本身可移植、可测试、心智模型更纯
- 希望减少 server 专属概念泄漏到业务编排

当前仓示例：`graph_src_v2`

---

## 3. 设计方法（面向“简单通用”）

### 3.1 奥卡姆剃刀：只保留一个主契约

- 业务动态参数统一走 `context`
- `config` 只承载执行控制参数（如 `recursion_limit`）
- 避免同义键散落在多处（`context`/`configurable`/headers）

### 3.2 框架分层（建议）

1. **Runtime Contract 层**：`RuntimeContext`（字段即业务能力边界）
2. **Resolve 层**：把 `context + config` 收敛为运行选项
3. **Compose 层**：组装 model/tools/middleware/skills/subagents
4. **Graph 层**：只做编排（节点与边）

### 3.3 扩展点最小集

- 模型扩展：`model_provider/model_name` 路由
- 工具扩展：`enable_local_mcp` + `mcp_servers`
- deepagent 扩展：`skills/subagents`
- 所有扩展都通过 `RuntimeContext` 入图

---

## 4. 路线选择建议（实操）

- 你现在这种“按场景混用 create_agent / create_deep_agent / custom graph”场景，**v2 更适合作为主线**。
- v2 能覆盖执行面动态能力（模型路由、MCP/tools/skills 动态装配）。
- v1 仅在控制面定制需求出现时启用（见第 8 节）。

建议执行策略：

1. 新 graph 默认按 v2（compiled graph）开发。
2. 租户隔离优先放在 Auth 层（`@auth.authenticate` + `@auth.on.*`）。
3. 仅当控制面需要按租户动态定制时，为该能力局部引入 v1 适配层。

---

## 5. 官方依据（URL）

### 5.1 `langgraph.json` 可指向 compiled graph 或工厂函数

- https://docs.langchain.com/oss/python/langgraph/application-structure  
  关键点：`graphs` 条目可配置为 compiled graph，或“构图函数（function that makes a graph）”。

### 5.2 Graph-native 的标准写法：`context_schema + Runtime[Context]`

- https://docs.langchain.com/oss/python/langgraph/graph-api  
  关键点：在 `StateGraph` 上定义 `context_schema`，节点通过 `Runtime[Context]` 读取 `runtime.context`。
- https://docs.langchain.com/oss/python/langgraph/use-graph-api  
  关键点：运行时用 `invoke(..., context=...)` 传参，避免污染 state。

### 5.3 `create_agent` 本质是 graph 运行时

- https://docs.langchain.com/oss/python/langchain/agents  
  关键点：`create_agent` 构建的是 graph-based agent runtime（底层 LangGraph）。
- https://docs.langchain.com/oss/python/langchain/runtime  
  关键点：`create_agent` 支持 `context_schema`，运行时通过 `context` 注入依赖。

### 5.4 Agent Server factory 的 `ServerRuntime` 语义

- 本地安装源码证据：`.venv/lib/python3.13/site-packages/langgraph_sdk/runtime.py`
  - `ServerRuntime` 是工厂入口 runtime 类型
  - 通过 `.execution_runtime` 收窄到执行态并读取 `context`
  - 非执行态（读 schema/read state）无执行 context
- 对应官方源码路径（GitHub）：
  - https://github.com/langchain-ai/langgraph/blob/main/libs/sdk-py/langgraph_sdk/runtime.py

### 5.5 生产鉴权与租户隔离（LangSmith/Auth）

- https://docs.langchain.com/langsmith/auth
  关键点：
  - 认证由 `@auth.authenticate` 提供用户身份
  - 授权由 `@auth.on.*` 在资源维度执行隔离
  - 用户信息进入运行配置上下文，可供运行时读取

---

## 6. 在本仓的落地映射

- v1（factory）：`graph_src_v1/langgraph.json`
- v2（compiled graph）：`graph_src_v2/langgraph.json`
- v2 RuntimeContext：`graph_src_v2/runtime/context.py`
- v2 assistant graph：`graph_src_v2/agents/assistant_agent/graph.py`
- v2 deepagent graph：`graph_src_v2/agents/deepagent_agent/graph.py`

这份文档是路线级决策文档；参数流转细节继续看：`26-context-config-runtime-flow.md`。

---

## 7. 选型决策树（v1 还是 v2）

按顺序回答下面 5 个问题：

1. 你是否必须在“每次 run 开始前”按请求动态重建依赖（例如临时 MCP 连接、强依赖 access context）？
   - 是：优先 **v1**
   - 否：继续 2

2. 你是否希望 graph 本身可在更多环境复用（弱化 server 专有语义）？
   - 是：优先 **v2**
   - 否：继续 3

3. 团队新人是否经常因为 runtime/factory 注入链路而理解成本过高？
   - 是：优先 **v2**
   - 否：继续 4

4. 当前主要目标是否是“短期快速交付 + 多 graph 统一动态调参接口”？
   - 是：优先 **v1**
   - 否：继续 5

5. 你是否已经出现明显的运行时行为漂移、重放困难、缓存优化受阻？
   - 是：把对应 graph 类别迁移到 **v2**
   - 否：保持当前路线，但统一 `context` 契约

一句话决策：

- **默认 v2**：业务编排与执行面统一走 graph-native。
- **按需 v1**：只有控制面/工厂阶段确需 `ServerRuntime` 再局部引入。

---

## 8. 租户隔离边界：v2 能做什么，v1 何时需要

### 8.1 v2 可以完成的（推荐主路径）

- 执行面租户隔离：按认证用户/权限动态过滤模型、MCP、tools、skills。
- 运行时策略：在节点中读取 `runtime.context` + auth 注入配置，进行租户策略决策。
- 安全原则：不信任客户端传入的 `context.user_id`，以 Auth 注入身份为真值。

### 8.2 需要 v1 的典型场景（控制面）

- 你要在 **factory 阶段** 按租户返回不同 graph/schema/introspection 结果。
- 你要根据 `access_context` 区分执行与读操作，并只在执行态初始化重资源。
- 你要在图生成前直接使用 `runtime.ensure_user()` 决定部署层资源装配。

### 8.3 真实判断规则

1. 仅执行面差异（run 时能力差异） -> 用 v2。
2. 控制面差异（assistants.read/schema/graph 视图差异） -> 用 v1。
3. 同项目可混用，但默认保持 v2 主线，v1 仅作薄适配层。
