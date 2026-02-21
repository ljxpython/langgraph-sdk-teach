# LangGraph Runtime Context / context_schema / Runnables 教学手册

这份文档专门讲你提到的三个核心概念：

- `context_schema`
- `runtime context`
- `runnables`

它们不是 SDK 的表层 API，但决定了你能不能把“动态模型/动态提示词/动态工具”做对。

---

## 1) 先建立一张图（心智模型）

在一次请求里，你会同时接触三类信息：

1. **State（状态）**：会被图节点读写，参与持久化
2. **Context（上下文）**：运行时输入给图，不建议当状态写回
3. **Config（配置）**：运行配置（如 `recursion_limit`、`configurable`）

你当前项目里，动态参数主要走的是：

- `config.configurable` -> `build_runtime_options(...)` -> `create_agent(...)`

对应代码：`graph_src/agent.py`

---

## 2) 什么是 `context_schema`

`context_schema` 的作用：

- 约束“运行时上下文”长什么样
- 让图节点知道可以安全读取哪些字段
- 避免你把一堆临时参数塞进 state 造成污染

一个极简例子（概念代码）：

```python
from dataclasses import dataclass

@dataclass
class ContextSchema:
    user_id: str
    system_prompt: str | None = None
    model_provider: str = "glm4"
```

重点：字段名是你自己定义的，不是框架硬编码。

---

## 3) 什么是 Runtime Context

Runtime Context 就是“本次调用临时上下文”。

常见用途：

- 当前用户是谁（`user_id`）
- 本次要求的语气/角色（`system_prompt`）
- 本次要用哪个模型（`model_provider`）
- 本次启用哪些工具（`mcp_servers`）

为什么重要：

- 你不用为每次请求改代码/改图
- 你可以做多租户差异化
- 你可以做 A/B 测试和灰度

在你项目里的落地（已实现）：

- `make_graph(config, runtime)` 中会读取 `runtime.execution_runtime.context`
- 然后把它交给 `build_runtime_options(...)` 做参数解析
- 当前 Agent Server 不允许同一请求同时传 `context` 和 `configurable`

---

## 4) 什么是 Runnables

`Runnable` 是 LangChain Core 的统一执行抽象。

你可以把它理解为：

- 一个“可调用对象”，支持 `invoke/ainvoke/stream/...`
- 模型、链、Agent、图节点都可以是 Runnable

在 LangGraph 里：

- 节点逻辑经常是 Runnable 或可包装成 Runnable
- 你在图里组合的是“执行单元”，不是普通函数堆砌

这就是为什么你会在代码里看到 `RunnableConfig`。

---

## 5) 这三个概念在你项目里的落地点

当前实现（已完成）：

- `make_graph(config, runtime)`：运行时工厂
- `build_runtime_options(config, runtime_context)`：从 `context` + `config.configurable` 提取动态参数
- `create_agent(model=..., tools=..., system_prompt=...)`：按运行参数组装

文件：`graph_src/agent.py`

也就是说你已经在“runtime 驱动图行为”的正确路径上了。

---

## 6) 你该怎么练（从易到难）

### 练习 A：只改 system prompt

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --config-json '{"configurable":{"system_prompt":"你必须用3条要点回答"}}'
```

目标：确认“运行时上下文/配置可以影响输出风格”。

### 练习 B：只改 model_provider

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --config-json '{"configurable":{"model_provider":"deepseek"}}'
```

目标：确认模型切换路径生效。

### 练习 B2：用 context 改模型

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请说明你使用的模型策略" \
  --context-json '{"model_provider":"kimi"}'
```

目标：确认 `context` 能直接驱动模型切换。

### 练习 C：指定 MCP 工具集

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请先计算2+3，再将hello反转" \
  --config-json '{"recursion_limit":60,"configurable":{"enable_local_tools":false,"enable_local_mcp":true,"mcp_servers":["local_math","local_text"]}}'
```

目标：确认 runtime 可以同时控制工具集和执行行为。

---

## 7) 常见误区

1. 以为 key 名是框架固定的
- 不是，`model_provider`/`mcp_servers` 是你项目自定义约定

2. 把所有东西塞到 state
- 用户配置、实验标签更适合 context/config，不应污染业务状态

3. 用旧 thread 验证新配置
- 旧上下文会干扰判断，建议关键实验用新 thread

4. 把 `recursion_limit` 放进 `configurable`
- 它应在 `config` 顶层

---

## 8) 学完这一章你应该会什么

- 知道 `context_schema` 是“运行时参数契约”
- 知道 runtime context/config 是“动态控制面”
- 知道 runnables 是“统一执行抽象”
- 能把“切模型/改提示词/切工具集”归到同一套架构思路

---

## 9) 关联阅读（你项目内）

- `docs/learning/langgraph-sdk/06-runtime-dynamic-config-playbook.md`
- `docs/learning/langgraph-sdk/07-local-mcp-playbook.md`
- `docs/learning/langgraph-sdk/03-runs-api-playbook.md`
