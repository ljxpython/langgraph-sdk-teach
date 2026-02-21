# Step 1：API 全景图（详细版）

## 目标

- 在 `http://127.0.0.1:8123/docs` 建立稳定的 API 心智模型。
- 先学对象和调用链，不做业务功能。

## 本地事实（基于你的 8123 OpenAPI）

- OpenAPI 标题：`LangSmith Deployment`
- tags：`Assistants`、`Threads`、`Thread Runs`、`Stateless Runs`、`Crons`、`Store`、`A2A`、`MCP`、`System`
- 你当前 Step 1 重点只看前 4 组。

## 先建立 4 个核心对象

- `assistant`：图的可调用实例（配置入口）。
- `thread`：会话容器（状态持久化）。
- `run`：一次执行（在 thread 上或无状态）。
- `state`：thread 当前/历史状态快照。

## 你必须掌握的主调用链

```text
assistant -> thread -> run -> state
```

对应端点（你本地已存在）：

1. `POST /assistants/search`
2. `POST /threads`
3. `POST /threads/{thread_id}/runs/stream` 或 `POST /threads/{thread_id}/runs/wait`
4. `GET /threads/{thread_id}/state`

## 动手任务（按顺序）

### Task A：识别 assistant

- 在 `/docs` 打开 `POST /assistants/search`
- 看请求体字段：`graph_id`、`metadata`、`limit`、`offset`
- 目标：理解 assistant 是“图入口”，不是会话本身。

### Task B：创建 thread

- 在 `/docs` 打开 `POST /threads`
- 看请求体字段：`thread_id`、`metadata`、`if_exists`、`ttl`
- 目标：理解 thread 才是状态容器。

### Task C：发起 run

- 在 `/docs` 比较两个端点：
  - `POST /threads/{thread_id}/runs/stream`
  - `POST /threads/{thread_id}/runs/wait`
- 关键字段：`assistant_id`（必填）、`input`、`stream_mode`
- 目标：理解 stream 与 wait 的差异。

### Task D：读取 state

- 在 `/docs` 看：
  - `GET /threads/{thread_id}/state`
  - `GET/POST /threads/{thread_id}/history`
- 目标：理解 state 是“当前快照”，history 是“演进轨迹”。

## Step 1 的最小验证（cURL）

> 本地 dev 常见情况下不需要 `X-Api-Key`；云端部署需要。

```bash
# 1) 查看 assistant 列表
curl -s -X POST http://127.0.0.1:8123/assistants/search \
  -H 'Content-Type: application/json' \
  -d '{"limit":10,"offset":0}'

# 2) 创建 thread
curl -s -X POST http://127.0.0.1:8123/threads \
  -H 'Content-Type: application/json' \
  -d '{}'

# 3) 在 thread 上发起 wait run（把 <THREAD_ID> 换掉）
curl -s -X POST http://127.0.0.1:8123/threads/<THREAD_ID>/runs/wait \
  -H 'Content-Type: application/json' \
  -d '{
    "assistant_id":"agent",
    "input":{"messages":[{"role":"human","content":"你好"}]}
  }'

# 4) 读取 state
curl -s http://127.0.0.1:8123/threads/<THREAD_ID>/state
```

## Step 1 的最小验证（Python SDK）

```python
import asyncio
from langgraph_sdk import get_client


async def main() -> None:
    client = get_client(url="http://127.0.0.1:8123")

    # 1) 查 assistant（等价于 POST /assistants/search）
    assistants = await client.assistants.search(limit=10, offset=0)
    print("assistants:", len(assistants))

    # 2) 建 thread（等价于 POST /threads）
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    print("thread_id:", thread_id)

    # 3) 发起 wait run（等价于 POST /threads/{thread_id}/runs/wait）
    result = await client.runs.wait(
        thread_id,
        "agent",
        input={"messages": [{"role": "human", "content": "你好"}]},
    )
    print("run_result:", result)

    # 4) 读 state（等价于 GET /threads/{thread_id}/state）
    state = await client.threads.get_state(thread_id)
    print("state_keys:", list(state.keys()))


if __name__ == "__main__":
    asyncio.run(main())
```

> 运行方式：`uv run python <your_script>.py`

也可以直接使用仓库内现成脚本：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py full-demo --message "你好"
```

## 概念辨析（必须会）

- 为什么 `assistant` 不是会话？
  - 因为会话上下文不存 assistant 上，而存 thread 上。
- 为什么 `runs/stream` 适合学习？
  - 它暴露中间步骤，能看到图执行过程。
- 为什么要看 `state/history`？
  - 这是理解“持久化执行”和“调试回放”的关键。

## 完成标准（全部满足才算过）

- 你能不看文档口述：assistant、thread、run、state 的职责。
- 你能解释 `runs/wait` 与 `runs/stream` 的差异场景。
- 你能跑通一次完整链路并拿到 `thread_id` 与 state。

## 官方对照阅读

- Server API 总览：
  - https://docs.langchain.com/langsmith/server-api-ref

## Assistants 深入学习

- 逐接口 Python SDK 调用清单：
- `docs/learning/langgraph-sdk/13-assistants-api-playbook.md`
