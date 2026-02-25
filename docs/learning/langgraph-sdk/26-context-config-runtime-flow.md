# context / config / runtime 参数流转说明（含签名疑惑解答）

## 1. 先给结论

- `context` 和 `config` 不是一回事。
- 在 LangGraph 0.6+ 语义里，`context` 是长期推荐入口；`config.configurable` 是兼容层。
- 在 **graph factory**（`make_graph(config, runtime)`）里，应使用 `ServerRuntime[Context]`，并通过 `runtime.execution_runtime` 读取执行态上下文。
- 在 **graph node**（节点函数）里，才是 `Runtime[Context]` 的典型使用场景。

---

## 2. 官方定义（结合本地已安装源码）

### 2.1 `Runtime[Context]`（节点运行时）

- 定义位置：`.venv/lib/python3.13/site-packages/langgraph/runtime.py`
- 语义：注入到图节点/中间件，提供 `context/store/stream_writer/previous`。
- 文档注释明确：`Runtime` 不包含 `config`，`config` 需通过 `RunnableConfig` 参数或 `get_config()` 读取。

### 2.2 `ServerRuntime[Context]`（Agent Server 工厂运行时）

- 定义位置：`.venv/lib/python3.13/site-packages/langgraph_sdk/runtime.py`
- 语义：仅用于 Agent Server 调用 graph factory 的场景。
- 关键点：
  - 工厂会在多种 access context 被调用（执行、读状态、读 schema 等）。
  - 只有执行场景（`threads.create_run`）才有 `context`。
  - 推荐通过 `runtime.execution_runtime` 做执行态收窄后再取 `context`。

### 2.3 `context` vs `config.configurable`

- 位置：`.venv/lib/python3.13/site-packages/langgraph_api/models/run.py`
- 关键规则：
  - 同一次 run 如果同时给了 `context` 和 `config.configurable`，会直接 400。
  - 报错原文：
    - `Cannot specify both configurable and context. Prefer setting context alone...`
    - `Context was introduced in LangGraph 0.6.0 and is the long term planned replacement for configurable.`

---

## 3. 你这个仓库里，参数到底是谁接收的？

下面是本仓真实调用链（从接口入参到 `make_graph`）：

1) FastAPI 入参接收  
- `fastapi_src/models/schemas.py`：`WaitChatRequest` 定义 `context/config`。

2) 服务层归一化  
- `fastapi_src/services/chat_service.py:normalize_context_and_config`：
  - 若同时出现 `context` + `config.configurable`，把 `configurable` 合并进 `context`，并移除 `configurable`。
  - 这是本仓的“context-only 兼容归一化”。

3) 调用 LangGraph API  
- `fastapi_src/services/chat_service.py:wait_chat` -> `client.runs.wait(..., context=..., config=...)`
- `fastapi_src/api/routes.py:chat_stream` -> `client.runs.stream(..., context=..., config=...)`

4) LangGraph API 接收与校验  
- `.venv/.../langgraph_api/api/runs.py`：`wait_run/create_run/stream_run` 接收 payload。
- `.venv/.../langgraph_api/models/run.py:create_valid_run`：
  - 读取 `context` 与 `config`。
  - 执行“不能同时传”的冲突校验。
  - 将结果写入 run kwargs（`config/context`）。

5) worker 执行时取值  
- `.venv/.../langgraph_api/stream.py:astream_state`：
  - `context = kwargs.pop("context", None)`
  - `config = kwargs.pop("config")`
  - 然后 `get_graph(..., access_context="threads.create_run")`

6) graph factory 参数注入  
- `.venv/.../langgraph_api/graph.py:get_graph`：
  - `server_runtime = build_server_runtime(...)`
  - `invoke_factory(value, graph_id, config, server_runtime)`
- `.venv/.../langgraph_api/_factory_utils.py`：
  - 由工厂签名分类器决定把 `config` 和 `server_runtime` 分别传给哪个参数。

7) 你的 `make_graph` 最终消费  
- `graph_src/agent.py:make_graph(config, runtime)`：
  - 从 `runtime.execution_runtime.context` 取运行时上下文。
  - `build_runtime_options(config, runtime_context)` 同时读取 `runtime_context` 与 `config.configurable`（当前实现 context 优先）。

一句话：
**接口参数先由 runs API 接收并写入 run kwargs，执行时由 stream/graph 层把 `config` 和 `server_runtime` 注入你的 factory，最终在 `make_graph` 被消费。**

### 3.1 直接 `curl` 调 LangGraph API（不是 FastAPI 转发）

下面这个例子直接打 LangGraph Server 的 Runs API：

```bash
curl -sS -X POST "http://127.0.0.1:8123/threads/<THREAD_ID>/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {"messages": [{"role": "user", "content": "你好"}]},
    "context": {
      "model_provider": "glm4",
      "system_prompt": "你是一个简洁助手",
      "temperature": 0.2
    },
    "config": {
      "recursion_limit": 60
    }
  }'
```

到 `make_graph(config, runtime)` 后，你关心的几个点可这样理解：

- `config.get("configurable", {})`
  - 在 Server 侧会由 `context` 同步填充而来（并叠加一些系统字段，例如请求/鉴权/header 映射等）。
  - 所以你通常能在这里拿到与 `context` 同源的业务动态参数。

- `runtime.context`
  - 这是 **`Runtime[Context]`（节点 runtime）** 的字段，不是 `ServerRuntime` factory 参数的字段。
  - 在 `make_graph` 这种 factory 里不应直接按这个字段取值。

- `runtime.execution_runtime`
  - 这是 `ServerRuntime` 的执行态收窄对象（`threads.create_run` 时非空）。
  - 你可以在这里拿到执行上下文对象；是否包含完整业务 `context`，取决于运行时实现与版本。
  - 在你当前仓库设计里，`config.configurable` 已提供稳定兜底，所以 factory 不会因为 `execution_runtime.context` 缺失而取不到参数。

---

## 4. 你问的这几个取值点，分别是什么角色？

### 4.1 `config.get("configurable", {})`

- 这是从 `RunnableConfig` 里拿“可配置字典”键值。
- 在本仓 `graph_src/agent.py` 里，它作为兼容来源（含 header 映射键，如 `x-model-provider`）。

### 4.2 `runtime.context`

- 这是 `Runtime[Context]`（节点运行时）上的字段，典型在 node 函数里用。
- 不属于 Agent Server graph factory 推荐入口。

### 4.3 `runtime.execution_runtime`

- 这是 `ServerRuntime` 的执行态收窄入口。
- 只有执行 run 时非空；读 schema/read state 等场景会是 `None`。
- 所以 factory 里要先判断它，再读 `execution_runtime.context`。

---

## 5. 为什么你看到有的地方 `Runtime` 不报错？

你提到的文件在另一个仓库里：

- `/Users/xxxxx/PycharmProjects/my_best/langchain_teach/graph_src_v2/agents/assistant_agent/graph.py`
- 对应注册：`/Users/xxxxx/PycharmProjects/my_best/langchain_teach/graph_src_v2/langgraph.json`

它的写法是：

- `langgraph.json` 导出的是 `.../graph.py:graph`（一个已编译 graph 对象），不是 `make_graph(config, runtime)` factory。
- `Runtime[ContextSchema]` 出现在节点函数 `_run_async(state, runtime, config)` 上。

所以它不报你说的 factory 签名错误，是正常的：

- 它走的是 **Graph API 节点 runtime 用法**（规范）；
- 不是 **Agent Server factory 参数分类器** 这条校验路径。

结论：

- 该文件的 `Runtime[ContextSchema]` 用法本身是规范的（节点场景）。
- 你之前说的 `(config, runtime: Runtime)` 报错，针对的是 factory 场景（例如 `make_graph`），两者不是同一层。

但“看起来不报错”常见有三类原因：

1) **它不是 factory，只是节点函数**  
   - 节点函数用 `Runtime[Context]` 完全合理。

2) **它不是当前被注册调用的 graph entry**  
   - 未被 `langgraph.json` 指向时，不会经过 factory 分类器，自然也不会触发报错。

3) **单参数工厂的“静默错配”**  
   - 分类器规则在 `.venv/.../langgraph_api/_factory_utils.py`：
     - 单参数若未识别为 `ServerRuntime`，会被当作 `config` 参数传入。
   - 所以 `def make_graph(runtime: Runtime): ...` 这种单参数 factory 可能“不报错”，但拿到的其实是 config，不是 runtime。
   - 双参数 `def make_graph(config, runtime: Runtime)` 则会因“必须是 ServerRuntime/RunnableConfig 组合”直接报错。

---

## 6. 设计建议（生产可执行）

1) **业务动态参数统一放 `context`**  
   - 如模型路由、system prompt、租户策略、工具开关、采样参数。

2) **`config` 只放执行控制项**  
   - 如 `recursion_limit`、durability、调度类参数。

3) **保留一层兼容适配（入口处做）**  
   - 只在 ingress 把旧 `config.configurable` 合并到 `context`；下游统一按 `context` 读。

4) **factory 类型固定为 `ServerRuntime[Context]`**  
   - 并通过 `runtime.execution_runtime` 判空后读 `context`。

5) **节点类型固定为 `Runtime[Context]`**  
   - 避免把 server 专用 runtime 泄漏进可移植图逻辑。

### 6.1 如果“同一次 run 里我想同时用 context 和 configurable 的优点”怎么办？

先明确：API 协议层不允许同请求同时显式传两套业务参数（`context` + `config.configurable`）。

正确做法是“先合并，再发送”：

1. 客户端先把两套候选参数 merge 成一个 `final_context`。
2. 冲突键按你定义的优先级决策（例如 `context` 优先，或白名单键按来源优先）。
3. 请求里只发送：
   - `context = final_context`
   - `config` 仅保留非 `configurable` 的执行控制参数（如 `recursion_limit`）。

可落地的简单优先级策略：

- 业务语义键（模型、prompt、工具开关、采样参数）统一以 `context` 为准。
- 执行控制键（递归深度、durability、调度）放在 `config`。
- 不允许同名键跨两处并存；若检测到则在客户端直接报错或记录告警并按策略覆盖。

---

## 7. 本仓可验证证据

- 冲突规则与 long-term replacement：`.venv/lib/python3.13/site-packages/langgraph_api/models/run.py`
- factory 参数分类逻辑：`.venv/lib/python3.13/site-packages/langgraph_api/_factory_utils.py`
- factory 注入点：`.venv/lib/python3.13/site-packages/langgraph_api/graph.py`
- 执行时 context/config 取值：`.venv/lib/python3.13/site-packages/langgraph_api/stream.py`
- 你自己的 factory 消费点：`graph_src/agent.py`
- 本仓 context-only 归一化：`fastapi_src/services/chat_service.py`
- 回归测试（合并 configurable -> context）：`tests/fastapi_test/test_fastapi_service_core.py`

---

## 8. `graph_src_v1` 最小改造清单（独立版本）

1. 修正包命名空间：`graph_src_v1` 内部 import 统一为 `graph_src_v1.*`。
2. 修正 graph 入口：`graph_src_v1/langgraph.json` 的 path 统一指向 `./graph_src_v1/...`。
3. 运行时参数契约：业务动态参数优先走 `context`，`config.configurable` 仅保留兼容兜底。
4. 执行控制参数：`recursion_limit` 等仅放在 `config` 顶层，不放 `configurable`。
5. 边界类型：factory 继续使用 `ServerRuntime[...]`；节点层使用 `Runtime[Context]`。

补充：`graph_src_v1` 里的 `assistant` 与 `deepagent_demo` 现已统一为 runtime factory 入口，可按每次 run 的 `context` 动态调整模型参数，并动态装配 MCP/tools/skills/subagents。

架构取舍（奥卡姆剃刀）：

- 近期默认保持 runtime factory（`make_graph(config, runtime)`）统一路径，先保证多 graph 动态调参的一致心智模型。
- 当出现“重复行为漂移 + 团队认知负担高 + 缓存/性能受阻 + 需要更强静态契约”中的两项及以上长期存在时，再把对应 graph 类别迁移到 pure graph-native compiled entry。

## 9. `graph_src_v2` 纯 graph-native 实践

- 新目录：`graph_src_v2`（从 `graph_src_v1` 复制后重构）。
- 入口改为 compiled graph：`graph_src_v2/langgraph.json` 指向 `.../graph.py:graph`。
- 统一运行时类型：`graph_src_v2/runtime/context.py` 的 `RuntimeContext`。
- 节点签名使用 `Runtime[RuntimeContext]`，并通过 `context` 动态解析模型、MCP/tools、deepagent skills/subagents。

进一步阅读：`27-v1-v2-framework-architecture-guide.md`（路线对比 + 设计方法 + 官方依据 URL）。

补充决策：当前主线按 `graph_src_v2` 演进；租户隔离默认走 Auth + v2 执行面策略。仅当需要控制面按租户定制（例如 factory 阶段 schema/introspection 差异）时，再局部引入 v1/`ServerRuntime` 适配层。详见 `27-v1-v2-framework-architecture-guide.md` 第 8 节。
