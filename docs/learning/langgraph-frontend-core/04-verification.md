# 04. 验收清单

## 手工验收

- [ ] 输入一句自然语言，前端能看到 `messages*` 增量输出
- [ ] 工具调用请求与工具结果能被区分显示
- [ ] Timeline 能看到 `updates/tasks/checkpoints/debug`
- [ ] 命中 `__interrupt__` 时能进入审批 UI
- [ ] 提交审批后流程可恢复至 `done/error`
- [ ] State 面板可回读本轮输入

### HITL 中断触发用例（`__interrupt__`）

前置：`assistant_id=deepagent_demo`

### 子 agent / 工具调用触发用例（可长期复用）

前置：`assistant_id=deepagent_demo`

1. 子 agent（`task`）触发

`请把“做一个前端平台改版”拆成3个子任务，并分别委托子代理执行后汇总结果。`

2. 工具调用（`write_todos`）触发

`请先创建一个待办清单：1) 调研 LangGraph stream_mode；2) 写出验证步骤；3) 输出风险项，然后继续执行。`

3. 文件工具（`write_file`/`edit_file`）触发

`请新建 docs/tmp_hitl_demo.md，写入“这是一次 HITL 测试”，然后把第一行改成“已通过 HITL 审批测试”。`

观察点：

- `Chat Panel` 出现 `tool_request/tool_result/state_progress`
- 命中中断时出现 `__interrupt__`
- 点击 `Approve Resume` 后继续执行到 `done/error`

推荐指令（按顺序）：

1. `请先创建一个待办清单：1) 调研 LangGraph stream_mode；2) 写出验证步骤；3) 输出风险项，然后继续执行。`
2. `请新建一个文件 docs/tmp_hitl_demo.md，内容包含“这是一次 HITL 测试”，并继续后续步骤。`
3. `请把 docs/tmp_hitl_demo.md 的第一行改成“已通过 HITL 审批测试”，然后继续执行。`

验收预期：

- [ ] 运行中出现 `__interrupt__` / `human_review_required`
- [ ] 点击 `Approve Resume` 后能继续执行
- [ ] 最终进入 `done` 或 `error` 终态

## 初始化阶段验收

- [ ] `frontend_src/` 已完成 React + TS + Vite 初始化
- [ ] 目录骨架文件已创建（pages/components/lib/store/types）
- [ ] 可执行 `npm run build` 且构建成功

## 本地联调启动（前后端）

```bash
# 1) LangGraph
uv run langgraph dev --port 8123 --no-browser

# 2) FastAPI（默认已允许 5173 跨域）
uv run uvicorn fastapi_src.app:app --reload --port 8011

# 3) Frontend
cd frontend_src
npm install
npm run dev
```

跨域说明：

- FastAPI 使用 `FASTAPI_CORS_ORIGINS` 控制允许来源。
- 默认允许 `http://127.0.0.1:5173` 与 `http://localhost:5173`。

## 回归参考

```bash
uv run --with pytest pytest tests/test_streaming_stage_s1.py tests/test_streaming_stage_s2.py tests/test_streaming_stage_s3_hitl_time_travel.py tests/test_streaming_stage_s4_unified_contract.py -vv -s
uv run --with pytest pytest tests/fastapi_test -vv -s
```
