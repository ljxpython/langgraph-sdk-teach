# LangGraph API 学习主线方案（前后端仅辅助）

## 学习目标

- 当前项目已可通过 `uv run langgraph dev --port 8123 --no-browser` 启动。
- 学习主目标：系统掌握 LangGraph API（对象模型、调用链、流式事件、状态管理）。
- 实现目标：做一个“可观察 API 行为”的演示前后端，服务于学习，不做重业务设计。

## 学习边界（确保不跑偏）

- 主线：只围绕 LangGraph API 学习与验证。
- 辅线：前端和 FastAPI 只用于“可视化 API 事件”，不是产品化 UI 开发。
- 验收标准：你能解释并实际跑通 assistants / threads / runs / state / stream。

## 你当前项目的已知基础

- 图配置：`langgraph.json`
  - graph 名称：`agent`
  - 入口：`./graph_src/agent.py:agent_not_deep`
- 这意味着你可以直接用 `assistant_id="agent"` 发起调用（或先 `assistants.search()` 获取 UUID）。

## 核心概念（先掌握这 3 个）

- `assistant`：图实例配置（对应你的 graph）。
- `thread`：会话状态容器（持久化上下文）。
- `run`：一次执行（可等待结果、可流式返回）。

## 学习路径（API 优先，按顺序）

### 第 1 步：建立 API 全景图

1. 启动：`uv run langgraph dev --port 8123 --no-browser`
2. 打开：`http://localhost:8123/docs`（或你的实际端口）
3. 先只看这几组端点：
   - `Assistants`
   - `Threads`
   - `Thread Runs`
   - `Stateless Runs`

输出物（必须完成）：

- 一张你自己的对象关系图：assistant -> thread -> run -> state。

### 第 2 步：跑通最小调用链（不做 UI）

顺序固定为：

1. 创建 thread（`threads.create` / `POST /threads`）
2. 在 thread 上发起 run（`runs.stream` 或 `runs.wait`）
3. 读取 thread state（`threads.get_state`）

输出物（必须完成）：

- 1 个最小脚本：能完整打印 run 事件和最终 state。

### 第 3 步：用 FastAPI 做 API 学习代理（后端辅助）

- 推荐模式：`Frontend(观察面板) -> FastAPI(事件转发) -> LangGraph Agent Server`
- 在后端维护最小 `user_id -> thread_id` 映射。
- 请求到来时：
  1. 读/建 thread_id
  2. 调 `runs.stream`（实时）或 `runs.wait`（阻塞）
  3. 把结果转发给前端

输出物（必须完成）：

- SSE 接口可以把 `updates/messages/tasks/checkpoints/debug` 全部透传。

### 第 4 步：前端仅做“事件可视化”（前端辅助）

- 聊天区：仅显示 `messages`。
- 步骤区：展示 `updates/tasks/checkpoints/debug` 时间线。
- 状态区：展示 `threads.get_state` 快照。

输出物（必须完成）：

- 一次对话中可看见每一步事件，不只最终答案。

## 两种调用模式怎么选（学习重点）

- `runs.stream`：需要打字机效果、节点进度、实时事件。
- `runs.wait`：你只要最终结果，前端不需要流式。
- 无状态请求：用 `POST /runs/stream`（threadless）。

## 认证与部署切换

- 本地开发：通常可直接访问本地 URL（如 `http://localhost:8123`）。
- 云端/受保护部署：需要 `X-Api-Key`。
  - Python SDK：`get_client(url=..., api_key=...)`
  - JS SDK：`new Client({ apiUrl, apiKey })`

## 最小 Python 示例（推荐先跑）

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8123")

# 1) 创建线程
thread = await client.threads.create()

# 2) 发起流式运行
async for chunk in client.runs.stream(
    thread["thread_id"],
    "agent",  # 来自 langgraph.json 的 graph 名
    input={"messages": [{"role": "human", "content": "你好"}]},
    stream_mode="updates",
):
    print(chunk.event, chunk.data)

# 3) 查看状态
state = await client.threads.get_state(thread["thread_id"])
print(state)
```

## 最小 JS 示例

```javascript
import { Client } from "@langchain/langgraph-sdk";

const client = new Client({ apiUrl: "http://localhost:8123" });
const thread = await client.threads.create();

const stream = client.runs.stream(thread.thread_id, "agent", {
  input: { messages: [{ role: "user", content: "你好" }] },
  streamMode: "updates",
});

for await (const chunk of stream) {
  console.log(chunk.event, chunk.data);
}
```

## 常用官方文档（重点）

- Agent Server API 总览：
  - https://docs.langchain.com/langgraph-platform/server-api-ref
- Streaming：
  - https://docs.langchain.com/langgraph-platform/streaming
- Threads：
  - https://docs.langchain.com/langgraph-platform/use-threads
- Deployment Quickstart：
  - https://docs.langchain.com/langsmith/deployment-quickstart

## 学习阶段里程碑（建议）

- M1：能解释每个核心端点作用，并用 cURL 调通。
- M2：能用 Python/JS SDK 跑通 thread + run + state。
- M3：能在前端看到完整流式事件轨迹。
- M4：能对比 `runs.wait` 与 `runs.stream` 的行为差异。

## 生产接入注意事项（后续）

- 每个用户固定 thread，避免上下文错乱。
- 为 run 请求增加超时、重试、日志追踪（至少记录 `thread_id`、`run_id`）。
- 流式断连场景优先使用可恢复策略（按需启用 `stream_resumable` / join stream）。
- 严禁把真实密钥提交到仓库。
