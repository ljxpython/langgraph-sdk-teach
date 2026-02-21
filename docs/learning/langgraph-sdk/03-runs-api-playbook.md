# Runs API 学习手册（官方文档分阶段重学版）

## 0. 这次重学的范围（对应官方）

本轮只学 Run 执行模型，按官方四篇文档组织：

1. Background runs
   - https://docs.langchain.com/langsmith/background-run
2. Same thread（多 assistant 共用线程）
   - https://docs.langchain.com/langsmith/same-thread
3. Stateless runs
   - https://docs.langchain.com/langsmith/stateless-runs
4. Cron jobs
   - https://docs.langchain.com/langsmith/cron-jobs

## 1. 先建立统一心智模型

- `assistant`：配置实例（默认模型/提示词/工具策略）
- `thread`：状态容器（是否保留上下文取决于是否传 thread）
- `run`：一次执行（真正消耗推理资源）

一句话：**Run 是执行核心，thread 决定是否有记忆，assistant 决定默认配置。**

## 2. 分阶段学习路径（重新开始）

### Stage R1：Stateful 基础执行（先稳住）

目标：掌握 `wait-run` 与 `stream-run`。

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread

uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "你好"

uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "请分两点回答"
```

验收：

- 你能解释 `wait`（一次性结果）和 `stream`（事件流）的差异。

### Stage R2：Background run（非阻塞执行）

官方对应：`background-run`。

目标：掌握 `create -> get/list -> join` 生命周期。

```bash
# 非阻塞创建 run（立即返回 run_id）
uv run python sdk_src/examples/langgraph_sdk_learn.py run-create \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "写3点总结"

# 查看该线程下 runs
uv run python sdk_src/examples/langgraph_sdk_learn.py run-list \
  --thread-id <THREAD_ID> \
  --limit 10 --offset 0

# 查询单个 run
uv run python sdk_src/examples/langgraph_sdk_learn.py run-get \
  --thread-id <THREAD_ID> \
  --run-id <RUN_ID>

# 等待 run 完成
uv run python sdk_src/examples/langgraph_sdk_learn.py run-join \
  --thread-id <THREAD_ID> \
  --run-id <RUN_ID>
```

验收：

- 你能看到 run 从 `pending/running` 到 `success/error` 的状态变化。

### Stage R3：Same thread（多 assistant 同一线程接力）

官方对应：`same-thread`。

目标：验证“线程不绑定单一 assistant”。

步骤：

1. 创建一个带特定 context 的 assistant（A）
2. 用 A 在同一 thread 上先跑一轮
3. 再换另一个 assistant（B 或默认 `agent`）在同一 thread 继续跑

```bash
# 创建 assistant A
uv run python sdk_src/examples/langgraph_sdk_learn.py assistant-create \
  --graph-id agent \
  --name "same-thread-A" \
  --context-json '{"system_prompt":"你是A角色"}'

# 创建 thread
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread

# 第1轮：assistant A
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id <ASSISTANT_A_UUID> \
  --message "我叫小王"

# 第2轮：换 assistant B（可直接用默认 agent）
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "我刚刚说我叫什么？"
```

验收：

- 第二轮能利用同一 thread 的历史信息作答。

### Stage R4：Stateless runs（无状态执行）

官方对应：`stateless-runs`。

目标：掌握“不传 thread_id 即无状态”。

```bash
# 无状态 wait
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --assistant-id agent \
  --message "只用一句话介绍你自己"

# 无状态 stream
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run \
  --assistant-id agent \
  --message "给我两条建议"
```

验收：

- 不需要 thread 也能执行。
- 适用于“单次问答、不保留会话”的场景。

### Stage R5：Cron jobs（定时触发执行）

官方对应：`cron-jobs`。

目标：掌握线程绑定 cron 与无状态 cron 的区别，以及清理要求。

注意：当前学习 CLI 暂未封装 cron 子命令，本阶段直接用 Python SDK。

```python
from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:8123")
assistant_id = "agent"

# 1) 线程绑定 cron（在同一 thread 上按计划运行）
thread = await client.threads.create()
cron_for_thread = await client.crons.create_for_thread(
    thread["thread_id"],
    assistant_id,
    schedule="27 15 * * *",  # UTC
    input={"messages": [{"role": "user", "content": "What time is it?"}]},
)

# 2) 无状态 cron（每次触发都新建 thread）
cron_stateless = await client.crons.create(
    assistant_id,
    schedule="27 15 * * *",  # UTC
    input={"messages": [{"role": "user", "content": "Daily report"}]},
    on_run_completed="delete",  # 默认 delete，可改 keep
)

# 3) 用完必须删除，避免额外费用
await client.crons.delete(cron_for_thread["cron_id"])
await client.crons.delete(cron_stateless["cron_id"])
```

验收：

- 你能说清楚 `create_for_thread` 与 `create` 的差异。
- 你知道 cron 表达式按 UTC 解析，且任务用完必须删除。

## 3. Run 阶段统一验证清单

- 能独立完成一次 background run 生命周期（create/list/get/join）
- 能完成 same-thread 双 assistant 接力
- 能完成 stateless wait/stream
- 能解释 cron 的 thread 模式和 stateless 模式

## 4. 生产注意事项（官方语义 + 工程实践）

1. Background run
- 适合长任务，前端轮询 `run-get` 或服务端 `run-join`。

2. Same-thread
- 强大但容易上下文污染；A/B 实验建议从同起点复制 thread。

3. Stateless
- 成本和延迟更可控，但无历史记忆。

4. Cron
- 全部按 UTC 解释。
- 结束后删除 cron，避免持续计费。
- 若 `on_run_completed="keep"`，要配合 TTL/清理策略。

## 5. 关联文档

- 主线入口：`docs/learning/langgraph-sdk/00-learning-path.md`
- 动态配置：`docs/learning/langgraph-sdk/06-runtime-dynamic-config-playbook.md`
- Assistant 配置：`docs/learning/langgraph-sdk/13-assistants-api-playbook.md`

## 6. 对应自动化测试（Stage 主流程）

- 测试文件：`tests/test_runs_stage_cases.py`
- 覆盖案例：
  - `R1` Stateful `wait + stream`
  - `R2` Background run 生命周期（`create/get/list/join`）
  - `R3` Same-thread 双 assistant 接力
  - `R4` Stateless `wait + stream`
  - `R5` Cron `create_for_thread + create + delete`

执行方式（显示详细步骤日志）：

```bash
uv run --with pytest pytest tests/test_runs_stage_cases.py -vv -s
```

## 7. 历史扩展内容（保留，不废弃）

上一版中关于这些内容依然有效，只是从 Run 主线中拆分出去，避免你在“重学 Run”时被混杂信息打断：

- 模型/提示词/MCP 的动态覆盖细节
- `context` 与 `configurable` 的项目内约束
- 运行时工厂与参数映射字段（如 `model_provider`、`mcp_servers`）

对应阅读：

- `docs/learning/langgraph-sdk/06-runtime-dynamic-config-playbook.md`
- `docs/learning/langgraph-sdk/13-assistants-api-playbook.md`
