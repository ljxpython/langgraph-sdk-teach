# Streaming Stage S3：HITL / Time Travel

## 0. 学习目标

这一章聚焦 3 个官方语义：

1. `interrupt` + `command.resume` 的人机协作闭环。
2. `threads.get_history` + `checkpoint_id` 的 time-travel 回放入口。
3. `threads.update_state` 的可选分叉能力与兼容降级。

官方依据：

- https://docs.langchain.com/langsmith/add-human-in-the-loop
- https://docs.langchain.com/langsmith/human-in-the-loop-time-travel

## 1. S3 核心结论

1. 动态 HITL 的标准信号是返回 `__interrupt__`，并通过 `command={"resume": ...}` 继续执行。
2. time-travel 的关键不是“重跑全部历史”，而是“从某个 checkpoint 继续，形成新分叉”。
3. 不同 SDK/部署版本对 `command`、`checkpoint_id`、`update_state` 的参数支持可能不一致，测试必须做能力探测。
4. 兼容优先级：先保证 `history` 可读与 run 可完成，再在支持时断言 resume/update_state 分支。

## 2. 与 S1/S2 的关系

- S1：基础流式闭环（`stream + wait + state`）。
- S2：高级流式语义（`subgraphs + join_stream + custom`）。
- S3：人机协作与历史分叉（`interrupt/command/checkpoint_id/update_state`）。

## 3. 前后端实现要点

后端（SSE 透传）继续保持：

- `event = chunk.event`
- `data = chunk.data`
- 统一补充 `done/error`

前端消费建议：

- 如果 run 结果中含 `__interrupt__`，渲染「待人工处理」状态。
- 恢复执行时，发送结构化 `command.resume`，不要把恢复信息塞进自然语言消息里。
- time-travel UI 以 `checkpoint_id` 为主键展示分叉入口。

## 4. 对应自动化测试（S3）

- 测试文件：`tests/test_streaming_stage_s3_hitl_time_travel.py`
- 覆盖点：
  - `interrupt_before` 与 `command` 能力探测
  - `threads.get_history` 的 checkpoint 可读性
  - `checkpoint_id` 与 `threads.update_state` 的可选分支（支持则校验，不支持则降级日志）

执行方式（详细日志）：

```bash
uv run --with pytest pytest tests/test_streaming_stage_s3_hitl_time_travel.py -vv -s
```

## 5. 验收标准

- 你能解释为什么 S3 必须是“能力探测优先”，而不是写死参数。
- 你能说明 `__interrupt__`、`command.resume`、`checkpoint_id` 三者关系。
- 你能在环境不支持 update_state 时给出不报错的降级路径。
