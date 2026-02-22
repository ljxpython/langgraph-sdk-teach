# 03. HITL 交互流程

## 触发

- 条件：run 结果中出现 `__interrupt__`

## 前端动作

1. 进入 `human_review_required`
2. 展示 `action_requests`（工具名/参数）
3. 按 `allowed_decisions` 渲染 `approve/edit/reject`

## 恢复

- 提交 `command.resume` 到后端
- 恢复后继续消费 stream，直到 `done/error`

## 失败处理

- 恢复失败：保留当前审批上下文并提示重试
- 记录 `thread_id/run_id/request_id`
