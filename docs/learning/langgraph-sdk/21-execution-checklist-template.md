# 执行清单模板（可打勾）

> 用法：复制本模板到你的 issue / PR / 周报，按顺序执行并打勾。

## A. 回归基线（先跑）

- [ ] 命令已执行：

```bash
uv run --with pytest pytest tests/test_streaming_stage_s1.py tests/test_streaming_stage_s2.py tests/test_streaming_stage_s3_hitl_time_travel.py tests/test_streaming_stage_s4_unified_contract.py -vv -s
```

- [ ] 全部通过（通过数 / 总数）：`__ / __`
- [ ] 日志中看到 `messages*`
- [ ] 日志中看到工具调用链顺序
- [ ] 日志中看到 `__interrupt__`
- [ ] 日志中看到 `join_stream` 边界说明

## B. S1 基础语义稳定性

- [ ] `request_idx < result_idx <= final_ai_idx`
- [ ] `messages/metadata` 兼容
- [ ] `messages/partial` 兼容

## C. S2 高级边界

- [ ] `subgraphs` 能力探测分支通过
- [ ] `join_stream` 允许 0 事件分支通过
- [ ] `run.join` 最终输出非空

## D. S3 HITL / time-travel 探测

- [ ] `interrupt` 分支（支持时）通过
- [ ] `command.resume` 分支（支持时）通过
- [ ] `checkpoint_id` 分支（支持时）通过
- [ ] `update_state` 分支（支持时）通过
- [ ] 不支持时降级路径可通过

## E. S4 综合契约

- [ ] 自然语言输入沉淀可回读
- [ ] LLM 流式输出可观测
- [ ] 工具请求/结果顺序可断言
- [ ] AI 最终输出可断言
- [ ] `join_stream` 边界可断言

## F. DeepAgent ToDo + HITL

- [ ] `write_todos` 可观测
- [ ] 分类为 `deepagent_todo`
- [ ] `__interrupt__` 可解析
- [ ] approve 后可继续执行

## G. 子智能体委托专项

- [ ] 中断动作里出现 `task`
- [ ] 最终消息里出现 `tool_calls[].name == "task"`
- [ ] 最终消息里出现 `type == "tool" and name == "task"`

## H. 前后端对接一致性核对（文档）

- [ ] 文档：`17-streaming-frontend-backend-standard.md`
- [ ] 仅依赖官方类型：`event/data/__interrupt__`
- [ ] 未定义额外业务协议（仅保留传输层 `done/error`）

## I. 验收矩阵核对（文档）

- [ ] 文档：`14-verification-matrix.md`
- [ ] S1~S4 + DeepAgent 条目齐全
- [ ] 命令与断言描述一致

## J. 学习闭环交付物

- [ ] 一页“SDK 事件 -> 前端行为”映射（含 Mermaid）
- [ ] 一页“`__interrupt__` 审批流程”说明
- [ ] 一份最新回归日志（含 `thread_id/run_id`）

## 本次执行记录（可追加）

- 执行人：`<name>`
- 日期：`<yyyy-mm-dd>`
- 环境：`LANGGRAPH_API_URL=<...>`
- 结果摘要：`<pass/fail + 关键说明>`

---

## 本轮进度（B~G 已打勾）

基于最近一次全量回归：

```bash
uv run --with pytest pytest tests/test_streaming_stage_s1.py tests/test_streaming_stage_s2.py tests/test_streaming_stage_s3_hitl_time_travel.py tests/test_streaming_stage_s4_unified_contract.py -vv -s
```

结果：`11 passed`

### B. S1 基础语义稳定性

- [x] `request_idx < result_idx <= final_ai_idx`
- [x] `messages/metadata` 兼容
- [x] `messages/partial` 兼容

### C. S2 高级边界

- [x] `subgraphs` 能力探测分支通过
- [x] `join_stream` 允许 0 事件分支通过
- [x] `run.join` 最终输出非空

### D. S3 HITL / time-travel 探测

- [x] `interrupt` 分支（支持时）通过
- [x] `command.resume` 分支（支持时）通过
- [x] `checkpoint_id` 分支（支持时）通过
- [x] `update_state` 分支（支持时）通过
- [x] 不支持时降级路径可通过

### E. S4 综合契约

- [x] 自然语言输入沉淀可回读
- [x] LLM 流式输出可观测
- [x] 工具请求/结果顺序可断言
- [x] AI 最终输出可断言
- [x] `join_stream` 边界可断言

### F. DeepAgent ToDo + HITL

- [x] `write_todos` 可观测
- [x] 分类为 `deepagent_todo`
- [x] `__interrupt__` 可解析
- [x] approve 后可继续执行

### G. 子智能体委托专项

- [x] 中断动作里出现 `task`
- [x] 最终消息里出现 `tool_calls[].name == "task"`
- [x] 最终消息里出现 `type == "tool" and name == "task"`
