# DeepAgent 规范案例：ToDo / Skills / Subagent / HITL

## 0. 目标

这章给出一个可直接运行的 DeepAgent 参考实现，并明确前后端应如何判定关键事件。

实现位置：

- 图实现：`graph_src/deepagent_example.py`
- 技能文件：`graph_src/skills/common/SKILL.md`
- 技能文件：`graph_src/skills/research/SKILL.md`
- 图注册：`langgraph.json` 中 `deepagent_demo`

## 1. 案例覆盖能力

1. ToDo 规划：使用 `TodoListMiddleware` 注入的 `write_todos`。
2. Skills：加载 `/skills/common` 与 `/skills/research`。
3. 子智能体：通过 `subagents` 注册 `research-subagent`。
4. 人机交互：通过 `interrupt_on` 对 `write_todos` / `write_file` / `edit_file` / `task` 设审批。

## 2. 关键代码说明

`deepagent_demo` 的核心参数：

- `backend=FilesystemBackend(root_dir=graph_src)`：将读写边界限制在 `graph_src`。
- `skills=["/skills/common", "/skills/research"]`：启用技能。
- `subagents=[...]`：配置 research 子代理。
- `interrupt_on={...}`：声明 HITL 触发点。

注意：在 LangGraph API 中不要在图里显式传 `checkpointer`，平台会自动处理持久化。

## 3. HITL 输出如何判定

当触发人工审批时，run 结果会包含 `__interrupt__`。

本仓已提供标准化解析函数：

- `normalize_hitl_interrupt(result)`

它会提取：

- `action_requests`（待审批工具调用）
- `allowed_decisions`（每个工具允许 `approve/edit/reject` 的集合）
- `resume_payload_example`（可直接用于恢复）

恢复执行示例：

```python
from graph_src.deepagent_example import build_resume_command

command = build_resume_command([
    {"type": "approve"},
])
```

## 4. 前端判定建议（本章专用）

1. 若结果包含 `__interrupt__`：UI 状态进入 `human_review_required`。
2. 展示 `action_requests[].tool_name` 与参数。
3. 根据 `allowed_decisions` 渲染可选按钮。
4. 用户确认后提交 `Command(resume={"decisions": [...]})`。

子智能体判定建议：

- 将 `tool_name == "task"` 视为子智能体委托请求。
- 在最终 run `messages` 中可观测到 `tool_calls.name == "task"` 与 `type == "tool" and name == "task"`，可作为“委托请求 + 委托结果”证据。

## 5. 启动与验证

启动服务后可直接指定：

- `assistant_id=deepagent_demo`

最小验证（示例）：

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id deepagent_demo \
  --message "先用todo列三步计划，再写入graph_src/demo_note.md"
```

通过标准：

- 观察到 `write_todos` 工具调用。
- 触发 HITL 时可从 `__interrupt__` 提取审批项。
- 审批后可继续执行并得到最终输出。

自动化对应：

- `tests/test_streaming_stage_s4_unified_contract.py`
- 其中 `test_streaming_stage_s4_deepagent_todo_hitl_resume_contract` 会断言 ToDo 分类 + HITL 中断恢复。
- 其中 `test_streaming_stage_s4_deepagent_subagent_delegate_and_tool_result` 会断言子智能体委托与子代理工具结果可观测。

## 6. 官方依据

- https://docs.langchain.com/oss/python/deepagents/customization
- https://docs.langchain.com/oss/python/deepagents/skills
- https://docs.langchain.com/oss/python/deepagents/human-in-the-loop
- https://docs.langchain.com/oss/python/langchain/middleware/built-in#to-do-list
