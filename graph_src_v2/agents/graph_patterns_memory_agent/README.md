# graph_patterns_memory_agent 逻辑说明

这个 demo 的目标是把 5 类能力放在一张图里：

- tools 调用
- 人机审批（HITL）
- 多智能体（supervisor + specialist）
- 子图（subgraph）
- 长期记忆（runtime.store）

## 1) 图的节点与职责

- `load_long_term_memory`
  - 从 `runtime.store` 读取当前用户（`user_id`）的历史偏好。
  - 命中后把记忆以 `SystemMessage` 注入到上下文。

- `human_review_gate`
  - 决定是否需要审批。
  - 如果是“记忆写入句式”（如 `记住:` / `remember:`），跳过审批并跳过 specialists。
  - 如果命中审批关键词（如 `request_human_approval`、`人工审批`、`send_demo_email`），调用 `interrupt(...)`。
  - 审批结果：
    - `reject`：设置 `approval_rejected=True`，后续不走 specialists。
    - `approve/edit`：继续走 specialists。

- `run_specialists_subgraph`
  - 这是子图节点，内部运行一个 supervisor agent。
  - supervisor 通过工具调用 specialist（`ask_knowledge_specialist` / `ask_ops_specialist`）。
  - 该子图不暴露 `send_demo_email`，避免绕过父图审批门。

- `persist_long_term_memory`
  - 检查用户输入是否是“记忆写入句式”。
  - 如果是，则 `runtime.store.aput(...)` 写入长期记忆，并返回确认消息。

- `finalize`
  - 收尾节点，返回消息。

## 2) 路由图（ASCII）

```text
START
  |
  v
[load_long_term_memory]
  |
  v
[human_review_gate] --(approval_rejected=True)--> [persist_long_term_memory]
        |                                           |
        |--(skip_specialists=True)------------------|
        |
        |--(normal path)--> [run_specialists_subgraph]
                               |
                               v
                        [persist_long_term_memory]
                               |
                               v
                            [finalize]
                               |
                               v
                              END
```

## 3) 什么时候审批，什么时候记录

### 3.1 走审批（HITL）

`human_review_gate` 中 `_requires_human_review(text)` 返回 `True` 时触发。

另外：只要识别到“发送邮件”意图（如“发邮件/发送邮件/email”），即使用户没有写
`request_human_approval`，也会自动先触发审批，再决定是否执行 `send_demo_email`。

决策解析采用 fail-closed：

- 仅接受 `approve` / `edit` / `reject`
- 缺失或非法决策视为无效，不会发送邮件
- `edit` 必须携带合法 `edited_action`，否则拒绝执行

当前关键词：

- `request_human_approval`
- `人工审批`
- `人工评审`
- `审批`
- `send_demo_email`

触发后会发出 `interrupt(...)`，payload 结构为：

- `action_requests`
  - `name`
  - `args`（兼容当前前端）
  - `arguments`（兼容官方命名）
  - `description`
- `review_configs`
  - `action_name`
  - `allowed_decisions = ["approve", "edit", "reject"]`

### 3.2 走记忆写入

`extract_memory_candidate(text)` 命中时（如 `记住: ...` / `remember: ...`）：

- 不触发审批
- 不走 specialists
- 直接到 `persist_long_term_memory` 写入 `runtime.store`

## 4) 核心判断伪代码

```python
if is_memory_input(user_text):
    skip_specialists = True
    approval_rejected = False
elif requires_human_review(user_text):
    decision = interrupt(review_payload)
    if decision == "reject":
        approval_rejected = True
        skip_specialists = True
    else:
        approval_rejected = False
        skip_specialists = False
else:
    approval_rejected = False
    skip_specialists = False

if approval_rejected or skip_specialists:
    goto persist_long_term_memory
else:
    goto run_specialists_subgraph -> persist_long_term_memory
```

## 5) 典型输入会发生什么

- `请先调用 request_human_approval 再执行任何上线动作...`
  - 命中审批关键词 -> `interrupt(...)` -> 前端审批 -> 再继续。

- `给 ops@example.com 发送邮件通知今晚灰度发布`
  - 自动识别邮件发送意图 -> `interrupt(...)` 审核邮件内容 -> 审批通过后执行 `send_demo_email`。

- `再次发一封邮件`
  - 若历史里有最近一次 `send_demo_email` 收件人：复用收件人并进入审批。
  - 若历史里没有可复用收件人：先返回追问（补充邮箱）而不是静默。

- `记住: 我偏好先灰度5%，观察10分钟再继续放量。`
  - 命中记忆写入 -> 跳过审批/子图 -> 直接写 store 并返回 `Long-term memory stored: ...`。

- `结合我之前的偏好，给我今晚上线方案`
  - 先加载历史记忆 -> 走 specialists 生成方案。

## 6) 本次排障总结（“没有下文”问题）

下面是这几轮真实问题和对应修复，便于后续排查：

1. 现象：启动服务直接失败（GraphLoadError）
   - 根因：在 LangGraph API 模式下，图中显式传入了自定义 `store` / `checkpointer`。
   - 修复：移除 `compile(..., store=...)` 与 `compile(..., checkpointer=...)`，改用平台托管 persistence。

2. 现象：触发审批后前端看不到可审批内容
   - 根因：interrupt payload 与前端约定不一致。
   - 修复：`action_requests` 同时提供 `args`（前端读取）和 `arguments`（官方文档命名），并保留 `review_configs` + `allowed_decisions`。

3. 现象：`记住: 我偏好先灰度5%...` 没有下文
   - 根因：该句包含“灰度”等词，被误判到审批路径。
   - 修复：记忆写入句式优先级最高（`extract_memory_candidate` 命中即跳过审批/子图，直接写长期记忆并返回确认消息）。

4. 现象：`再次发一封邮件` 没有下文
   - 根因：输入是邮件意图但信息不足，之前可能进入不稳定分支；同时部分前端在中断前不会显示额外 AI 文本。
   - 修复：
     - 先判断是否邮件意图；
     - 能从上下文提取最近一次 `send_demo_email` 收件人则复用并进入审批；
     - 提取不到收件人则明确追问（返回 AI 提示补充邮箱），避免静默。

5. 现象：审批前只有用户消息，看起来“没回复”
   - 说明：这是 `interrupt(...)` 的正常语义——节点在中断点暂停，恢复后才继续产出后续消息。
   - 建议：前端应优先渲染 `__interrupt__` 卡片，而不是依赖中断前 AI 文本。
