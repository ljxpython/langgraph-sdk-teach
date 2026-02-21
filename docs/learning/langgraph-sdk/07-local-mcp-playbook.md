# 本地 MCP 学习手册（FastMCP + LangGraph 动态加载）

## 学习目标

- 自己实现一个 MCP Server
- 在 LangGraph 运行时按参数动态加载 MCP 工具
- 同时支持“切模型 / 切提示词 / 开关 MCP”

## 官方对应能力

- LangChain MCP：
  - https://docs.langchain.com/oss/python/langchain/mcp
- LangGraph 运行时配置：
  - https://docs.langchain.com/oss/python/langgraph/use-graph-api#add-runtime-configuration
- LangSmith 运行时重建图：
  - https://docs.langchain.com/langsmith/graph-rebuild

## 本项目实现

- MCP 服务：`graph_src/local_mcp_server.py`
  - `add(a, b)`
  - `multiply(a, b)`
  - `square(n)`
- MCP 服务：`graph_src/local_text_mcp_server.py`
  - `reverse_text(text)`
  - `text_length(text)`
- 运行时动态加载：`graph_src/agent.py`
  - `get_local_mcp_tools()` 使用 `MultiServerMCPClient` + `stdio`
  - `enable_local_mcp=true` + `mcp_servers` 控制加载哪个工具集

## 最佳实践范例（推荐顺序）

### 1) 只开本地 MCP，其他保持默认

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请使用工具计算 (12 + 8) * 3" \
  --config-json '{"configurable":{"enable_local_mcp":true,"mcp_servers":["local_math"],"enable_local_tools":false}}'
```

### 2) 同时切模型 + 切系统提示词 + 开 MCP

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --config-json '{"configurable":{"model_provider":"kimi","system_prompt":"你是数学助教，优先调用工具再回答","enable_local_mcp":true,"mcp_servers":["local_math"]}}'
```

### 2.1) 工具集模式（多 MCP 同时加载）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请先计算 3*7，再把 result 反转" \
  --config-json '{"configurable":{"enable_local_mcp":true,"mcp_servers":["local_math","local_text"],"enable_local_tools":false}}'
```

### 3) 对照实验（同一 thread 基线拷贝）

- A 组：`enable_local_mcp=false`
- B 组：`enable_local_mcp=true,mcp_servers=["local_math","local_text"]`
- 比较 run 输出与 state/history

## 关键实现逻辑（简化版）

1. 运行时参数进入 `config.configurable`
2. `build_runtime_options` 解析参数
3. `build_agent_from_config` 根据开关装配 tools
4. `make_graph` 每次 run 动态创建 agent

## 常见问题

### Q1：为什么 MCP 用 stdio？

- 本地学习最简单，启动和调试成本最低。
- 你能完整看清 `MCP Server -> MCP Client -> Agent Tool` 链路。

### Q2：为什么工具函数要写 docstring？

- MCP/FastMCP 会把它作为工具说明暴露给模型。
- 没有描述，工具可用性和模型选择质量都会下降。

### Q3：生产环境也用 stdio 吗？

- 学习项目可以。
- 真生产通常会转成 HTTP/streamable-http 的 MCP 服务，便于治理和扩缩容。
