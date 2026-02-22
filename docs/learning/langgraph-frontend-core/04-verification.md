# 04. 验收清单

## 手工验收

- [ ] 输入一句自然语言，前端能看到 `messages*` 增量输出
- [ ] 工具调用请求与工具结果能被区分显示
- [ ] Timeline 能看到 `updates/tasks/checkpoints/debug`
- [ ] 命中 `__interrupt__` 时能进入审批 UI
- [ ] 提交审批后流程可恢复至 `done/error`
- [ ] State 面板可回读本轮输入

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
