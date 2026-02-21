# DeepAgent 实战：ToDo / Skills / 文件工具

## 0. 学习目标

本章只解决三件事：

1. DeepAgent 的 ToDo 能力是否需要自定义。
2. Skills 与工具的边界是什么。
3. 文件工具（读写/编辑/检索）在事件流里如何机读判定。

官方依据：

- https://docs.langchain.com/oss/python/deepagents/overview
- https://docs.langchain.com/oss/python/deepagents/harness
- https://docs.langchain.com/oss/python/deepagents/skills
- https://docs.langchain.com/oss/python/deepagents/customization
- https://docs.langchain.com/oss/python/langchain/middleware/built-in#to-do-list

## 1. 关键结论（先记住）

1. ToDo 不需要你手写工具。官方 `TodoListMiddleware` 会注入 `write_todos`。
2. DeepAgent Harness 默认包含文件工具能力（`ls/read_file/write_file/edit_file`，并支持 `glob/grep`）。
3. Skills 是“按需加载的任务知识包”，不是工具替代品。
4. 前端事件分类应以 `tool_name` 为主，不靠自然语言猜测。

## 2. 最小示例：创建 DeepAgent

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    system_prompt="你是可靠的软件工程助理",
)
```

说明：默认 DeepAgent harness 已包含计划、文件系统、子代理等能力；后续再按需叠加自定义工具或 skills。

## 3. ToDo 能力如何判断

### 3.1 运行时信号

- 工具调用名出现 `write_todos`
- 参数通常包含条目数组与状态字段（如 `pending/in_progress/completed`）

### 3.2 前端机读规则（建议）

```text
if tool_name == "write_todos":
    category = "tool_deepagent_todo"
```

## 4. Skills 的定位与判定

### 4.1 定位

- Skills 提供任务知识与流程指引（`SKILL.md`）
- DeepAgent 启动时先读 frontmatter；命中任务后再展开完整内容（progressive disclosure）

### 4.2 判定建议

- 事件层通常仍表现为模型/工具执行；skill 本身不一定对应独立事件类型
- 实践里用“结果行为”判定：是否触发了 skill 指定的工具链和流程

## 5. 文件工具能力与分类

建议前端将以下工具统一归类为 `tool_deepagent_fs`：

- `ls`
- `read_file`
- `write_file`
- `edit_file`
- `glob`
- `grep`

机读规则：

```text
if tool_name in {"ls","read_file","write_file","edit_file","glob","grep"}:
    category = "tool_deepagent_fs"
```

## 6. 与本项目 Streaming 对接

你当前项目的 SSE 转发是：

- 后端：`sdk_src/examples/langgraph_fastapi_observer.py`
- 输出：`event: <chunk.event>` + `data: <chunk.data>`

因此 DeepAgent 的 ToDo/文件行为在前端依然走“工具调用链”展示，不需要新增协议层，只需补工具分类白名单。

## 7. 验收标准

- 你能解释“为什么 ToDo 不必自定义”。
- 你能给出 `write_todos` 与文件工具的机读分类规则。
- 你能说明 skills 与 tools 的职责边界。

## 8. 规范案例入口

- DeepAgent 规范案例：`20-deepagent-canonical-example.md`
- 图实现：`graph_src/deepagent_example.py`
- HITL 输出解析：`normalize_hitl_interrupt(result)`
