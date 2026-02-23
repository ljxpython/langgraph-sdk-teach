# Context-Only 策略与踩坑总结

## 背景

在本项目联调中，出现了如下错误：

`Cannot specify both configurable and context. Prefer setting context alone. Context was introduced in LangGraph 0.6.0 and is the long term planned replacement for configurable.`

该错误出现在同一次 run 请求里同时传递 `context` 与 `config.configurable` 时。

## 官方资料证据

1. LangChain Forum 讨论（官方社区）
- URL: https://forum.langchain.com/t/considering-config-configurable-vs-context/1226
- 关键原文：
  - `Context was introduced with the update of Langgraph to 0.6.0`
  - 报错原文：`Cannot specify both configurable and context. Prefer setting context alone...`

2. LangGraph Issue #6342（官方仓库）
- URL: https://github.com/langchain-ai/langgraph/issues/6342
- 关键原文：
  - `Cannot specify both configurable and context. Prefer setting context alone.`
  - `Context was introduced in LangGraph 0.6.0 and is the long term planned replacement for configurable.`

3. LangGraph Streaming 文档（官方）
- URL: https://docs.langchain.com/oss/python/langgraph/streaming
- 关键点：stream 参数和事件语义以官方接口为准（`messages/updates/custom/debug/...`），前后端不应自定义第二套语义层。

## 本次踩坑原因

前端在同一次请求里同时提交了：

- `context_json`（例如 `system_prompt`）
- `config_json`（例如 `configurable.temperature`）

后端透传到 `runs.stream` 时触发冲突。

## 统一策略（落地规范）

1. **统一走 `context`**（包括模型动态参数）
   - `temperature`
   - `max_tokens`
   - `top_p`
   - `system_prompt`

2. `config` 仅保留非 `configurable` 的运行控制参数（如递归限制等），且与业务语义隔离。

3. 后端执行 context-only 归一化：
   - 若同时出现 `context` 与 `config.configurable`，将 `configurable` 合并进 `context`（context 优先），并移除 `configurable`。

## 代码实现要点（本仓）

- 归一化入口：`fastapi_src/services/chat_service.py` -> `normalize_context_and_config`
- stream/wait 都执行该归一化，再调用 SDK
- graph 层从 `runtime.context` 读取模型参数：`graph_src/agent.py`

## 验证方式

```bash
uv run --with pytest pytest tests/fastapi_test -vv -s
uv run --with pytest pytest tests/test_runtime_context_model_params.py -vv -s
```

## 新增踩坑：`Thread or assistant not found`

### 现象

- 前端 stream/wait 调用偶发 404，报错：`Thread or assistant not found`。

### 根因（本次定位）

- 本地 `user_id -> thread_id` 持久化后，LangGraph 侧该 thread 可能已不存在（服务重启、数据清理、环境切换）。
- 后端直接复用旧 thread_id 时，SDK 抛出 NotFound。

### 修复策略

1. `ensure_thread` 先做 thread 存在性校验（`client.threads.get(existing)`）。
2. 若校验失败，判定为 stale thread，自动新建 thread 并回写 SQLite 映射。
3. 后续 run 走新 thread，避免前端继续收到 404。

### 回归用例（本仓）

- `tests/fastapi_test/test_fastapi_service_core.py`
  - `test_wait_and_state_roundtrip`：验证已存在线程可复用。
  - `test_wait_recreates_stale_thread`：验证 stale thread 可自动重建。

### 排查清单

1. 核对 `LANGGRAPH_API_URL` 与当前 LangGraph 实例是否一致。
2. 核对 `assistant_id` 是否存在（默认 `agent`）。
3. 若仅 thread 404：清理本地持久映射或触发自动重建流程。
4. 若 assistant 404：检查 `langgraph.json` 图注册与 dev server 启动目录。

## 新增案例：`system_prompt` 已传入，但回答看起来“没生效”

### 现象

- 前端设置了 `system_prompt`（例如：`你是小明`），但问“你是谁”时，模型仍可能回答“我是 AI 助手...”。
- 从 state metadata 可看到：`system_prompt` 已存在于 run 元数据中。

### 判定

- 该场景通常不属于“链路失败”。
- 只要 run metadata 中出现 `system_prompt`，即可判定前端 -> FastAPI -> LangGraph 的传递链路已生效。

### 原因

- `你是小明` 属于弱约束提示，不能保证每次输出都严格命中指定措辞。
- 非零采样参数（如 `temperature=0.7`）会增加回复多样性，进一步降低文案稳定性。

### 推荐验证方法（可复现）

1. 使用强约束提示词，例如：
   - `你必须始终自称“小明”，当用户问“你是谁”时只能输出“我是小明”。`
2. 将 `temperature` 临时设为 `0` 进行稳定性验证。
3. 连续多次提问“你是谁”，观察输出一致性。
4. 同时检查 state metadata 中 `system_prompt/temperature` 是否与提交值一致。

### 学习项目中的结论

- “metadata 命中”用于验证链路是否生效。
- “文案是否完全一致”取决于提示词约束强度与采样参数，不应混同为链路故障。
