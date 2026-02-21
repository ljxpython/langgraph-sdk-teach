# Step 2：SDK 最小调用链

## 目标

- 用 SDK 跑通：创建线程 -> 运行 -> 读状态。

## 任务

1. Python SDK：`threads.create` + `runs.stream` + `threads.get_state`
2. 可选 JS SDK：同样流程跑一遍
3. 记录关键字段：`thread_id`、`assistant_id`、`run_id`

## 完成标准

- 输出一段日志，能看到事件流和最终 state。

## 深入学习入口

- Threads 详细手册：`docs/learning/langgraph-sdk/04-threads-api-playbook.md`
