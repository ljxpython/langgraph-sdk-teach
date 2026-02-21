# Assistants API 学习手册（整理版）

## 1. 先说结论（避免再混淆）

- 你的理解是对的：`assistants.create(..., context=...)` 是官方推荐方式。
- 动态配置有两层：
  - Assistant 层（持久化默认配置）
  - Run 层（单次调用临时覆盖）
- 所以不是“只能在 run 时改模型/提示词/工具”。

参考：

- https://docs.langchain.com/langsmith/assistants
- https://docs.langchain.com/langsmith/configuration-cloud

## 2. 核心心智模型

- `graph_id`：图程序（逻辑骨架）
- `assistant_id`：该图的一个配置实例（可版本化）
- `thread_id`：会话状态容器
- `run`：一次执行（assistant + thread + input）

一句话：**Graph 定义逻辑，Assistant 定义默认配置，Run 定义本次执行。**

## 3. Python SDK 对照（你最关心）

### 3.1 Assistant 层：创建默认配置

```python
openai_assistant = await client.assistants.create(
    "agent",  # graph_id
    context={"model_name": "openai"},
    name="Open AI Assistant"
)
```

### 3.2 Run 层：执行时临时覆盖

```python
result = await client.runs.wait(
    thread_id,
    openai_assistant["assistant_id"],
    input={"messages": [{"role": "user", "content": "hello"}]},
    context={"model_name": "deepseek"},
)
```

## 4. 全链路真实调用验证案例（可直接复现）

目标：验证“Assistant 默认配置生效 + Run 临时覆盖生效 + 覆盖不回写 Assistant”。

前置：本地服务已启动，默认 URL 为 `http://127.0.0.1:8123`。

### Step A：创建带 context 的 assistant（持久化默认配置）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-create \
  --graph-id agent \
  --name "assistant-e2e-context" \
  --context-json '{"model_provider":"glm4","system_prompt":"你是一个简洁助手"}'
```

记录返回中的 `assistant_id`，记为 `<ASSISTANT_UUID>`。

### Step B：创建 thread

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
```

记录返回中的 `thread_id`，记为 `<THREAD_ID>`。

### Step C：不传 run 级覆盖，验证继承 assistant 默认配置

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id <ASSISTANT_UUID> \
  --message "你好，请只回复ok" \
  --config-json '{"recursion_limit":60}'
```

通过标准：

- 返回成功
- 消息正常（示例可得到 `ok`）

### Step D：传 run 级覆盖（仅本次生效）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id <ASSISTANT_UUID> \
  --message "请说明你本次的角色设定" \
  --context-json '{"system_prompt":"你是本次临时覆盖角色"}' \
  --config-json '{"recursion_limit":60}'
```

通过标准：

- 返回成功
- 这次输出体现覆盖后的角色指令

### Step E：回读 assistant，确认默认配置未被 run 覆盖污染

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-get \
  --target-assistant-id <ASSISTANT_UUID>
```

通过标准：

- `context` 仍是 Step A 创建时的值
- Step D 的 run 覆盖不会写回 assistant

### Step F：清理（避免测试垃圾）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-delete \
  --target-assistant-id <ASSISTANT_UUID>

uv run python sdk_src/examples/langgraph_sdk_learn.py thread-delete \
  --thread-id <THREAD_ID>
```

## 5. CLI 命令和官方语义对齐

本仓库脚本已支持你要的方式：

- `assistant-create --context-json ...` -> `client.assistants.create("agent", context=...)`
- `assistant-update --context-json ...` -> 新建 assistant 版本并更新默认配置
- `wait-run/stream-run --context-json ...` -> run 级临时覆盖

脚本位置：`sdk_src/examples/langgraph_sdk_learn_assistants.py`

## 6. 验收清单

- 你能解释 Assistant 层和 Run 层各自负责什么。
- 你能独立跑通 Step A~F。
- 你能确认 run 覆盖不回写 assistant。

## 7. 常见错误（直接避坑）

1. 把 `graph_id` 当 `assistant_id` 用在 `assistant-get/update/delete`
- 现象：404 或解析失败

2. 在一个 run 里同时传 `context` 和 `configurable`
- 现象：400（当前服务约束）

3. 忘记 `recursion_limit`
- 现象：`GraphRecursionError`
- 建议：在 `--config-json` 顶层传 `{"recursion_limit":60}`

## 8. 关联文档

- 动态配置（运行时与覆盖策略）：`docs/learning/langgraph-sdk/06-runtime-dynamic-config-playbook.md`

## 9. 自动化测试文件（全链路）

- 测试文件：`tests/test_assistant_thread_run_flow.py`
- 覆盖链路：创建 assistant -> 创建 thread -> 默认运行 -> run 临时覆盖 -> 回读校验 -> 清理

执行方式：

```bash
uv run --with pytest pytest tests/test_assistant_thread_run_flow.py -vv -s
```

可选环境变量：

- `LANGGRAPH_API_URL`（默认 `http://127.0.0.1:8123`）
- `LANGGRAPH_GRAPH_ID`（默认 `agent`）
- `LANGGRAPH_RECURSION_LIMIT`（默认 `60`）
