# 04. 验收与回归

## 本地启动

```bash
uv run langgraph dev --port 8123 --no-browser
uv run uvicorn fastapi_src.app:app --reload --port 8011
```

## 最小验收命令

```bash
curl -s -X POST http://127.0.0.1:8011/api/thread -H "Content-Type: application/json" -d '{"user_id":"u-demo"}'
curl -s -X POST http://127.0.0.1:8011/api/chat/wait -H "Content-Type: application/json" -d '{"user_id":"u-demo","message":"你好，给我三条学习建议","assistant_id":"agent"}'
curl -s -X POST http://127.0.0.1:8011/api/chat/resume -H "Content-Type: application/json" -d '{"user_id":"u-demo","assistant_id":"deepagent_demo","command":{"resume":{"decisions":[{"type":"approve"}]}}}'
curl -N "http://127.0.0.1:8011/api/chat/stream?user_id=u-demo&assistant_id=agent&message=请先算2%2B3再输出结果"
curl -s "http://127.0.0.1:8011/api/state?user_id=u-demo"
```

## 通过标准

- `thread_id` 可复用
- `wait` 有最终文本
- `stream` 有连续事件并有 `done/error`
- `state` 可回读已执行输入

## 自动化回归（推荐）

```bash
uv run --with pytest pytest tests/test_streaming_stage_s1.py tests/test_streaming_stage_s2.py tests/test_streaming_stage_s3_hitl_time_travel.py tests/test_streaming_stage_s4_unified_contract.py -vv -s
uv run --with pytest pytest tests/fastapi_test -vv -s
```
