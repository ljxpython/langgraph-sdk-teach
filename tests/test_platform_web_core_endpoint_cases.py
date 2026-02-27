from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Mapping

import requests
from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if _as_mapping(message).get("type") == "ai":
            return str(_as_mapping(message).get("content", ""))
    return ""


def _message_texts_from_state(state: Any) -> list[str]:
    values = _as_mapping(state).get("values", {})
    messages = _as_mapping(values).get("messages", [])
    return [str(_as_mapping(item).get("content", "")) for item in messages]


def _log(message: str) -> None:
    print(f"[PLATFORM-WEB-CORE] {message}")


def test_platform_web_core_endpoint_cases() -> None:
    # Given: 默认连接到本地 LangGraph 服务，assistant_id 为 agent。
    # 这些环境变量与现有测试保持一致，便于在 CI/本地复用。
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))

    # Given/When: 直接调用 /info，验证服务存活且返回 JSON 对象。
    # Then: 这一步失败通常说明服务没启动或 URL 配置错误，后续步骤不具备执行前提。
    _log("Step 1/6 检查 /info")
    info_resp = requests.get(f"{url.rstrip('/')}/info", timeout=10)
    assert info_resp.status_code == 200
    assert isinstance(info_resp.json(), dict)

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            # Given: 生成唯一 tag，避免与历史测试数据冲突。
            # When: 创建 thread 并按 metadata 搜索。
            # Then: 能检索回刚创建的 thread，证明 /threads 与 /threads/search 路径可用。
            _log("Step 2/6 创建 thread 并校验 threads.search")
            tag = f"platform-web-core-{uuid.uuid4().hex[:8]}"
            thread = await client.threads.create(metadata={"tag": tag, "graph_id": assistant_id})
            thread_id = str(_as_mapping(thread).get("thread_id", ""))
            assert thread_id

            hit = await client.threads.search(metadata={"tag": tag}, limit=20, offset=0)
            hit_ids = {str(_as_mapping(item).get("thread_id", "")) for item in hit}
            assert thread_id in hit_ids

            # Given: 已有 thread，使用 runs.stream 触发一次流式执行。
            # When: 订阅 updates/messages 事件。
            # Then: 至少收到一个非空 payload，说明 /runs/stream 的 SSE 通道可消费。
            _log("Step 3/6 校验 runs.stream 流式返回")
            has_stream_payload = False
            query_stream = "请给我两条学习建议，并保持简洁。"
            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": query_stream}]},
                config={"recursion_limit": recursion_limit},
                stream_mode=["updates", "messages"],
            ):
                data = getattr(chunk, "data", None)
                if isinstance(data, Mapping) and data:
                    has_stream_payload = True
                    break
            assert has_stream_payload

            # Given: 非阻塞创建 run，拿到 run_id。
            # When: 通过 join_stream 重新接入该 run 的流，再用 join 等待最终结果。
            # Then: 最终 AI 文本非空，证明 /runs/{run_id}/stream 与 join 生命周期可用。
            _log("Step 4/6 校验 runs.join_stream 与 runs.join")
            created = await client.runs.create(
                thread_id,
                assistant_id,
                input={
                    "messages": [
                        {
                            "role": "human",
                            "content": "请输出不少于10条编号建议，每条一句说明。",
                        }
                    ]
                },
                config={"recursion_limit": recursion_limit},
            )
            run_id = str(_as_mapping(created).get("run_id", ""))
            assert run_id

            joined_events = 0
            async for _ in client.runs.join_stream(
                thread_id,
                run_id,
                stream_mode=["messages", "updates"],
            ):
                joined_events += 1

            joined_result = await client.runs.join(thread_id, run_id)
            assert len(_last_ai_content(joined_result).strip()) > 0

            # Given: 已执行过多轮 run。
            # When: 读取 state/history。
            # Then: state 中能看到测试输入，history 至少有一条，验证状态沉淀链路正常。
            _log("Step 5/6 校验 threads.get_state / get_history")
            state = await client.threads.get_state(thread_id)
            texts = _message_texts_from_state(state)
            assert any(query_stream in text for text in texts)

            history = await client.threads.get_history(thread_id, limit=10)
            assert len(history) >= 1

            _log(f"Step 5 通过: joined_events={joined_events}, history_len={len(history)}")

        finally:
            # Then(always): 无论前面断言是否失败都清理 thread，避免污染测试环境。
            _log("Step 6/6 清理 thread")
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())
