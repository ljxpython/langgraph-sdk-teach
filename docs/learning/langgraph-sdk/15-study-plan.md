# LangGraph SDK 学习计划（API 主线）

## 总目标

- 能独立解释并调用：`assistants`、`threads`、`runs`、`state`、`stream`。
- 能在自己的 FastAPI + 前端中可视化 LangGraph 执行步骤。

## 阶段计划

### Phase 1：认知建立（Step 1-2）

- 建立 API 对象模型：assistant -> thread -> run -> state
- 跑通 SDK 最小链路（创建线程、发起 run、读取 state）

### Phase 2：行为观察（Step 3-5）

- 掌握 stream 事件类型（messages/updates/tasks/checkpoints/debug）
- 用 FastAPI 透传流式事件
- 前端按事件类型可视化时间线

### Phase 3：总结固化（Step 6）

- 用 checklist 验收
- 形成自己的调用模板

## 学习节奏（建议）

- 每次只做一个 Step。
- 每个 Step 完成后必须保留运行截图或日志片段。
- 没有可运行证据，视为未完成。

## 开始顺序

1. 先读 `01-step-01-api-map.md`
2. 再做 `02-step-02-sdk-minimal.md`
3. 然后按 03 -> 06 依次推进
