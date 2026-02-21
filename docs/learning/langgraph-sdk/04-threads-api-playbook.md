# Threads API 学习手册（分阶段细化版）

## 0. 你现在所在位置

- 你已完成：Run 重学 + Threads T1/T2/T3/T4 实践
- 你现在要学：**Streaming（事件流观测）**

官方参考：

- https://docs.langchain.com/langsmith/use-threads

## 1. 先定心智模型

- `thread`：状态容器（时间轴）
- `run`：执行动作（往时间轴写入新状态）
- `state`：当前快照（最新状态）
- `history`：历史快照序列（演进轨迹）
- `thread-copy`：复制同起点，做公平对比实验

一句话：**Thread 决定上下文连续性，Run 决定状态如何演进。**

## 2. 学习阶段总览

### T1：状态闭环（已完成）

- create-thread -> wait-run -> state -> history

### T2：元数据治理（已完成）

- thread-update -> thread-get -> thread-search -> thread-count

### T3：实验设计（已完成）

- 用 `thread-copy` 做同起点 A/B
- 保证只改一个变量，避免上下文污染

### T4：生命周期治理

- thread-delete
- 归档与 TTL 思维（生产环境）

## 3. T1 详细回顾（便于复习）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread

uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_ID> \
  --assistant-id agent \
  --message "我叫小王，请记住我的名字"

uv run python sdk_src/examples/langgraph_sdk_learn.py state --thread-id <THREAD_ID>
uv run python sdk_src/examples/langgraph_sdk_learn.py history --thread-id <THREAD_ID> --limit 10
```

验收：

- `state.values.messages` 可见消息
- `history` 至少有 1 条以上记录

## 4. T2 详细回顾（便于复习）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-update \
  --thread-id <THREAD_ID> \
  --metadata-json '{"user_id":"u1","biz":"demo","graph_id":"agent"}'

uv run python sdk_src/examples/langgraph_sdk_learn.py thread-get --thread-id <THREAD_ID>

uv run python sdk_src/examples/langgraph_sdk_learn.py thread-search \
  --status idle \
  --metadata-graph-id agent \
  --limit 10 --offset 0

uv run python sdk_src/examples/langgraph_sdk_learn.py thread-count \
  --status idle \
  --metadata-graph-id agent
```

验收：

- `thread-get.metadata` 与更新值一致
- `search/count` 结果逻辑一致

## 5. T3（下一步）详细实操：同起点 A/B 实验

目标：你要证明“同一个问题，不同策略的差异来自策略本身，而不是历史污染”。

### Step 1：准备基线 thread

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py create-thread
```

记下 `<BASE_THREAD_ID>`。

### Step 2：给基线 thread 注入相同起始上下文

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <BASE_THREAD_ID> \
  --assistant-id agent \
  --message "请记住：项目主题是 LangGraph SDK 学习。"
```

### Step 3：复制出 A/B 两个分支线程

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-copy --thread-id <BASE_THREAD_ID>
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-copy --thread-id <BASE_THREAD_ID>
```

分别记为 `<THREAD_A>`、`<THREAD_B>`。

### Step 4：A/B 只改一个变量

示例变量：system prompt（A 简洁，B 详细）。

```bash
# A 组：简洁风格
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_A> \
  --assistant-id agent \
  --message "给出今天学习计划" \
  --context-json '{"system_prompt":"请只给3条简洁要点"}'

# B 组：详细风格
uv run python sdk_src/examples/langgraph_sdk_learn.py wait-run \
  --thread-id <THREAD_B> \
  --assistant-id agent \
  --message "给出今天学习计划" \
  --context-json '{"system_prompt":"请给分阶段详细计划并给验收标准"}'
```

### Step 5：对比结果（state/history）

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py state --thread-id <THREAD_A>
uv run python sdk_src/examples/langgraph_sdk_learn.py state --thread-id <THREAD_B>

uv run python sdk_src/examples/langgraph_sdk_learn.py history --thread-id <THREAD_A> --limit 10
uv run python sdk_src/examples/langgraph_sdk_learn.py history --thread-id <THREAD_B> --limit 10
```

### T3 验收标准

- A/B 起点一致（都来自 `<BASE_THREAD_ID>` 的 copy）
- A/B 仅改一个变量
- 输出差异可归因到该变量
- 你能解释为什么“直接在同一 thread 连续跑 A 再跑 B”不公平

## 6. T4：生命周期治理（清理与归档）

学习阶段建议：每轮实验结束，清理临时 thread。

```bash
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-delete --thread-id <BASE_THREAD_ID>
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-delete --thread-id <THREAD_A>
uv run python sdk_src/examples/langgraph_sdk_learn.py thread-delete --thread-id <THREAD_B>
```

生产建议：

- 给 thread 加 metadata（租户、场景、实验标签）
- 配置 TTL/归档策略，避免状态无限增长

## 7. 常见误区与排错

1. 误区：thread 就是一次请求
- 正解：thread 是容器，run 才是请求

2. 误区：A/B 在同一 thread 连续跑
- 正解：用 `thread-copy` 做同起点

3. 现象：`search` 没搜到目标
- 检查 `status` 过滤条件
- 检查 metadata 键名是否一致（如 `graph_id`）

4. 现象：`history` 看起来很短
- 新线程很正常，先执行几轮 run 再观察

## 8. 对应自动化测试

### Stage T1

- 测试文件：`tests/test_threads_stage_t1.py`
- 执行命令：

```bash
uv run --with pytest pytest tests/test_threads_stage_t1.py -vv -s
```

### Stage T2

- 测试文件：`tests/test_threads_stage_t2.py`
- 执行命令：

```bash
uv run --with pytest pytest tests/test_threads_stage_t2.py -vv -s
```

### Stage T3

- 测试文件：`tests/test_threads_stage_t3.py`
- 执行命令：

```bash
uv run --with pytest pytest tests/test_threads_stage_t3.py -vv -s
```

### Stage T4

- 测试文件：`tests/test_threads_stage_t4.py`
- 执行命令：

```bash
uv run --with pytest pytest tests/test_threads_stage_t4.py -vv -s
```

## 9. 你现在就做什么

你的下一步就是：**进入 Streaming 学习**（事件流观测与调试）。

建议操作：

1. 用 `stream-run` 跑 `updates/messages/tasks/checkpoints`
2. 对比 `wait-run` 与 `stream-run` 输出粒度差异
3. 记录一条完整事件轨迹用于排错
