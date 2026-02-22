# 02. 事件到 UI 映射

## 最小分类

1. `ai_stream`
- 条件：`event` 以 `messages` 开头
- 行为：追加文本流

2. `tool_request`
- 条件：payload 含 `tool_calls`
- 行为：显示工具名与参数

3. `tool_result`
- 条件：`type == "tool"` 或有 `tool_call_id`
- 行为：显示执行结果

4. `state_progress`
- 条件：`event in {updates,tasks,checkpoints,debug,values}`
- 行为：更新时间线

5. `run_terminal`
- 条件：`done` / `error` / `__interrupt__`
- 行为：结束、报错或进入审批态

## 子智能体 task 判定

- 委托请求：`tool_calls[].name == "task"`
- 委托结果：`type == "tool" and name == "task"`
