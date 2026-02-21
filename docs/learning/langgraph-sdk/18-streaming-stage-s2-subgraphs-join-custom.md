# Streaming Stage S2：subgraphs / join_stream / custom

## 0. 学习目标

这一章聚焦 3 个官方语义：

1. `subgraphs=True` 的流式输出兼容策略。
2. `join_stream` 的“只看加入后尾流”边界。
3. `custom` 模式与机读事件分类规则。

官方依据：

- https://docs.langchain.com/oss/python/langgraph/streaming
- https://docs.langchain.com/langsmith/streaming

## 1. S2 核心结论

1. `subgraphs=True` 可能返回带命名空间的信息；消费端要做兼容解析，不要假设唯一数据形状。
2. 不同 SDK 版本对 `runs.stream(..., subgraphs=True)` 的参数支持不一致，测试需先做能力探测再决定是否传参。
3. `join_stream` 适合断线后“重新接入实时流”，不保证补发加入前历史事件；若加入时 run 已接近完成，可能观测到 0 条尾流。
4. 计划/进度类信息应走 `custom`（结构化 JSON），不要混在自然语言 token 里。

## 2. 与 S1 的关系

- S1（`tests/test_streaming_stage_s1.py`）解决基础闭环：`stream + wait + state`。
- S2（`tests/test_streaming_stage_s2.py`）解决高级语义：`subgraphs + join_stream + 机读分类`。

## 3. 前后端实现要点

后端（本仓 SSE 透传）保持：

- `event = chunk.event`
- `data = chunk.data`
- 统一追加 `done/error`

前端消费建议：

- `messages` 系列事件按前缀匹配（如 `messages/metadata`、`messages/partial`）。
- 工具来源按工具名白名单分层：`deepagent_todo` / `deepagent_fs` / `local_tool` / `mcp_tool`。

## 4. 对应自动化测试（S2）

- 测试文件：`tests/test_streaming_stage_s2.py`
- 覆盖点：
  - `subgraphs` 能力探测 + 流式契约与命名空间兼容解析
  - `run-create -> join_stream -> run-join` 尾流重接（允许 0 条尾流）
  - 工具来源机读分类规则（可单元化校验）

执行方式（详细日志）：

```bash
uv run --with pytest pytest tests/test_streaming_stage_s2.py -vv -s
```

## 5. 验收标准

- 你能解释为什么 `join_stream` 不能被当作“历史回放 API”。
- 你能给出 `messages*` 事件前缀匹配而非单值匹配的原因。
- 你能实现并通过工具来源机读分类断言。
