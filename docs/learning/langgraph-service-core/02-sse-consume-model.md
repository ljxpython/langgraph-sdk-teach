# 02. SSE 消费模型

## 前端最小状态机

```text
run_started -> model_streaming -> tool_calling -> tool_completed -> final_answer -> run_done
                               \-> human_review_required -> command.resume -> (回到流)
任何状态 -> run_error
```

## SDK 输出到前端行为

- `messages*` -> `model_streaming`
- `tool_calls` -> `tool_calling`
- `type == tool` 或 `tool_call_id` -> `tool_completed`
- `__interrupt__` -> `human_review_required`
- `done` -> `run_done`
- `error` -> `run_error`

## 子智能体委托（task）判定

- 请求：`tool_calls[].name == "task"`
- 结果：`type == "tool" and name == "task"`
