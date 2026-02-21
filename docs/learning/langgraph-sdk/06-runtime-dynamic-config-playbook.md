# Runtime 动态配置学习手册（整理版）

## 1. 目标

这章只解决一件事：**如何稳定地动态改模型、提示词、工具集（含 MCP）**。

## 2. 官方语义（先定边界）

动态配置不是单层，而是两层：

1. Assistant 层（持久化默认配置）
- `assistants.create/update(..., context=...)`

2. Run 层（单次请求覆盖）
- `runs.wait/stream(..., context/config/...)`

你的示例属于第 1 层，完全正确：

```python
openai_assistant = await client.assistants.create(
    "agent",
    context={"model_name": "openai"},
    name="Open AI Assistant"
)
```

参考：

- https://docs.langchain.com/langsmith/assistants
- https://docs.langchain.com/langsmith/configuration-cloud

## 3. 本项目动态字段（统一口径）

`graph_src/agent.py` 当前读取这些字段：

- `model_provider`（兼容 `llm_provider`）
- `system_prompt`（兼容 `system_message`）
- `enable_local_tools`
- `enable_local_mcp`
- `mcp_servers`（兼容 `mcp_server`）

## 4. 一套可直接复现的全链路验证

与 `13-assistants-api-playbook.md` 保持一致，这里聚焦动态配置行为验证。

### 4.1 创建 assistant 默认配置（持久化）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-create \
  --graph-id agent \
  --name "runtime-e2e-default" \
  --context-json '{"model_provider":"glm4","system_prompt":"你是默认角色"}'
```

记下 `<ASSISTANT_UUID>`。

### 4.2 创建 thread

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
```

记下 `<THREAD_ID>`。

### 4.3 不覆盖，验证走 assistant 默认配置

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id <ASSISTANT_UUID> \
  --message "你好，请只回复ok" \
  --config-json '{"recursion_limit":60}'
```

### 4.4 单次 run 覆盖 system_prompt

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id <ASSISTANT_UUID> \
  --message "说明你当前角色" \
  --context-json '{"system_prompt":"你是一次性覆盖角色"}' \
  --config-json '{"recursion_limit":60}'
```

### 4.5 回读 assistant，确认 run 覆盖不回写

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-get \
  --target-assistant-id <ASSISTANT_UUID>
```

检查 `context.system_prompt` 是否仍为“你是默认角色”。

### 4.6 清理

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-delete \
  --target-assistant-id <ASSISTANT_UUID>

uv run python sdk_src/examples/langgraph_sdk_learn.py thread-delete \
  --thread-id <THREAD_ID>
```

## 5. MCP 动态开关最小案例

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请调用 add 计算 2+3，只输出结果" \
  --config-json '{"recursion_limit":60,"configurable":{"enable_local_tools":false,"enable_local_mcp":true,"mcp_servers":["local_math"]}}'
```

通过标准：

- 执行成功
- 输出包含 `5` 或语义等价结果

## 6. 学习模式 vs 生产模式（术语说明）

- “学习硬约束 / 生产软约束”是本项目的工程训练术语，不是官方 API 名词。
- 学习阶段：建议单轨（先固定只用 `context`）减少噪音。
- 生产阶段：可双轨兼容（保留 `configurable`），按调用方逐步迁移。

## 7. 常见问题与修复

1. `Cannot specify both configurable and context`
- 原因：同一 run 请求里同时传了 `context` 和 `configurable`
- 修复：一次请求只保留一个入口

2. `GraphRecursionError`
- 修复：在 `--config-json` 顶层加 `{"recursion_limit":60}`

3. `InternalServerError`（常见于工具循环）
- 修复：先简化提示词和工具开关，缩小到最小可复现请求再逐步加回

## 8. 关联文档

- Assistant 语义和命令：`docs/learning/langgraph-sdk/13-assistants-api-playbook.md`

## 9. 对应自动化验证

- 测试文件：`tests/test_assistant_thread_run_flow.py`
- 验证内容：Assistant 默认配置生效、Run 临时覆盖生效、覆盖不回写 Assistant、并完成资源清理

执行方式：

```bash
uv run --with pytest pytest tests/test_assistant_thread_run_flow.py -vv -s
```
