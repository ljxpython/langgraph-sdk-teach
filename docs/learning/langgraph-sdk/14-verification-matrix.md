# 知识点验证对照表

| 知识点 | 必跑命令 | 看到什么才算通过 |
|---|---|---|
| 创建会话 | `create-thread` | 返回 JSON 含 `thread_id` |
| 同步执行 | `wait-run` | 返回最终结果 |
| 流式执行 | `stream-run` | 控制台持续出现 `event=...` |
| 状态快照 | `state` | 有 `values/messages` 或 checkpoint 信息 |
| 历史回放 | `history` | 返回多条历史状态 |
| run 创建 | `run-create` | 返回 `run_id` |
| run 查询 | `run-list` + `run-get` | 能定位指定 `run_id` |
| run 等待 | `run-join` | 指定 run 完成并返回结果 |
| run 取消 | `run-cancel` | 返回取消确认 |
| 动态模型/提示词/MCP | `stream-run --config-json ...` | run kwargs/configurable 出现你传的字段 |
| Runtime Context 驱动 | `wait-run --context-json ...` | 行为按 context 参数生效（可切模型/提示词/工具集） |
| A/B 对照 | `thread-copy` | 得到新 thread_id，可独立运行 |
| Streaming S1 基础闭环 | `pytest tests/test_streaming_stage_s1.py -vv -s` | 覆盖 stream+wait+state，且 messages/tool 链断言通过 |
| Streaming S2 进阶语义 | `pytest tests/test_streaming_stage_s2.py -vv -s` | 覆盖 subgraphs 能力探测、join_stream 尾流边界（含 0 事件）、机读分类规则 |
| Streaming S3 HITL/Time Travel | `pytest tests/test_streaming_stage_s3_hitl_time_travel.py -vv -s` | 覆盖 interrupt/command/checkpoint_id/update_state 能力探测、历史 checkpoint 获取与兼容降级策略 |
| DeepAgent 规范案例 | `wait-run --assistant-id deepagent_demo` | 可观测到 write_todos/文件工具/子代理 task，并能从 __interrupt__ 提取审批动作 |
| Streaming S4 综合契约 | `pytest tests/test_streaming_stage_s4_unified_contract.py -vv -s` | 单组用例覆盖自然语言输入、LLM流式输出、工具请求/结果、AI最终输出、ToDo分类、HITL中断恢复、join_stream 边界 |
| Auth 认证失败语义 | 访问受保护接口时不提供凭证 | 返回 401，且错误语义明确为认证失败 |
| Auth 授权失败语义 | 使用已认证但低权限身份访问受限动作 | 返回 403，且错误语义明确为权限不足 |
| Auth owner 隔离 | 用 A 身份创建资源，再用 B 身份读取 | B 被拒绝或结果中不可见该资源 |

## 常用命令模板

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run --thread-id <THREAD_ID> --assistant-id agent --message "你好"
uv run python sdk_src/examples/langgraph_sdk_learn.py stream-run --thread-id <THREAD_ID> --assistant-id agent --message "你好"
```
