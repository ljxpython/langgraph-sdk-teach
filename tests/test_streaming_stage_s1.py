from __future__ import annotations

import asyncio
import os
from typing import Any, Mapping

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _thread_id_from(payload: Any) -> str:
    value = _as_mapping(payload).get("thread_id")
    if not isinstance(value, str) or not value:
        raise AssertionError("缺少合法 thread_id")
    return value


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if _as_mapping(message).get("type") == "ai":
            return str(_as_mapping(message).get("content", ""))
    return ""


def _state_texts(state: Any) -> list[str]:
    values = _as_mapping(state).get("values", {})
    messages = _as_mapping(values).get("messages", [])
    return [str(_as_mapping(msg).get("content", "")) for msg in messages]


def _log(message: str) -> None:
    print(f"[STREAM-S1] {message}")


def _iter_mappings(value: Any):
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _iter_mappings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_mappings(item)


def _message_text(value: Any) -> str:
    if hasattr(value, "content"):
        return str(getattr(value, "content", "") or "")
    return str(_as_mapping(value).get("content", "") or "")


def test_streaming_stage_s1_stream_wait_state() -> None:
    # ==================== Streaming S1 测试目标 ====================
    # 验证完整链路：创建 thread -> stream-run 观察事件 -> wait-run 对照 -> state 沉淀校验 -> 清理
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))

    stream_query = "请给我两条学习建议"
    wait_query = "你好，请只回复ok"

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            # Step 1: 创建 thread
            _log("Step 1/5 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)
            _log(f"Step 1 完成: thread_id={thread_id}")

            # Step 2: 流式执行并采集事件类型
            _log("Step 2/5 执行 stream-run 并统计事件")
            seen_events: set[str] = set()
            payload_chunks = 0
            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": stream_query}]},
                config={"recursion_limit": recursion_limit},
                stream_mode=["updates", "messages", "tasks", "checkpoints", "debug"],
            ):
                seen_events.add(str(getattr(chunk, "event", "")))
                if chunk.data and isinstance(chunk.data, Mapping):
                    payload_chunks += 1
            _log(f"Step 2 事件类型: {sorted(seen_events)}")
            _log(f"Step 2 payload 块数: {payload_chunks}")
            assert payload_chunks > 0
            assert len(seen_events) > 0
            assert bool({"updates", "messages", "tasks", "checkpoints", "debug"}.intersection(seen_events))

            # Step 3: 非流式执行（结果对照）
            _log("Step 3/5 执行 wait-run 观察最终结果")
            wait_result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": wait_query}]},
                config={"recursion_limit": recursion_limit},
            )
            wait_text = _last_ai_content(wait_result)
            _log(f"Step 3 输出: {wait_text}")
            assert len(wait_text) > 0

            # Step 4: 读取 state，确认消息沉淀
            _log("Step 4/5 读取 state 验证消息沉淀")
            state = await client.threads.get_state(thread_id)
            texts = _state_texts(state)
            assert any(stream_query in text for text in texts)
            assert any(wait_query in text for text in texts)
            _log(f"Step 4 校验通过: state messages={len(texts)}")

        finally:
            # Step 5: 清理资源
            _log("Step 5/5 清理 thread")
            if thread_id is not None:
                await client.threads.delete(thread_id)
                _log(f"Step 5 删除 thread 完成: {thread_id}")

    _log("开始执行 Streaming S1 自动化测试")
    asyncio.run(_run())
    _log("Streaming S1 自动化测试完成")


def test_streaming_stage_s1_messages_tuple_metadata() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            _log("S1-MSG Step 1/3 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            _log("S1-MSG Step 2/3 stream_mode=messages 采集 metadata")
            seen_messages_event = False
            seen_metadata = False
            seen_langgraph_node = False
            non_empty_chunks = 0

            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "请给我一句简短建议"}]},
                stream_mode=["messages"],
            ):
                event_name = str(getattr(chunk, "event", ""))
                if event_name.startswith("messages"):
                    seen_messages_event = True

                data = getattr(chunk, "data", None)
                if isinstance(data, (list, tuple)) and len(data) == 2:
                    msg_chunk, metadata = data[0], data[1]
                    if isinstance(metadata, Mapping):
                        seen_metadata = True
                        if isinstance(metadata.get("langgraph_node"), str):
                            seen_langgraph_node = True
                    if _message_text(msg_chunk).strip():
                        non_empty_chunks += 1
                    continue

                if isinstance(data, list):
                    for item in data:
                        if _message_text(item).strip():
                            non_empty_chunks += 1

                if event_name == "messages/metadata":
                    for mapping in _iter_mappings(data):
                        metadata = _as_mapping(mapping.get("metadata"))
                        if metadata:
                            seen_metadata = True
                            if isinstance(metadata.get("langgraph_node"), str):
                                seen_langgraph_node = True
                    continue

                mapping = _as_mapping(data)
                metadata = _as_mapping(mapping.get("metadata"))
                if metadata:
                    seen_metadata = True
                    if isinstance(metadata.get("langgraph_node"), str):
                        seen_langgraph_node = True

            _log(
                "S1-MSG Step 2 结果: "
                f"event={seen_messages_event}, metadata={seen_metadata}, "
                f"langgraph_node={seen_langgraph_node}, non_empty_chunks={non_empty_chunks}"
            )

            assert seen_messages_event
            assert seen_metadata
            assert seen_langgraph_node

            _log("S1-MSG Step 3/3 校验通过")
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_streaming_stage_s1_tool_chain_order() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            _log("S1-TOOL Step 1/3 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            _log("S1-TOOL Step 2/3 强制触发 to_upper 并采集顺序")
            request_idx: int | None = None
            result_idx: int | None = None
            final_ai_idx: int | None = None
            seen_to_upper = False

            query = (
                "你必须调用名为 to_upper 的工具, 参数 text='hello world'。"
                "禁止直接给出答案, 必须先调用工具, 最后仅输出工具结果。"
            )
            context = {
                "enable_local_tools": True,
                "enable_local_mcp": False,
                "system_prompt": "你必须严格按用户要求先调用工具再作答。",
            }

            chunk_index = 0
            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": query}]},
                context=context,
                stream_mode=["updates", "messages", "tasks", "debug"],
            ):
                chunk_index += 1
                data = getattr(chunk, "data", None)

                for mapping in _iter_mappings(data):
                    tool_calls = mapping.get("tool_calls")
                    if isinstance(tool_calls, list) and tool_calls:
                        names = [str(_as_mapping(tc).get("name", "")) for tc in tool_calls]
                        if any(name == "to_upper" for name in names):
                            seen_to_upper = True
                        if request_idx is None:
                            request_idx = chunk_index

                    if str(mapping.get("type", "")) == "tool" and result_idx is None:
                        result_idx = chunk_index

                    if str(mapping.get("type", "")) == "ai":
                        content = str(mapping.get("content", "") or "")
                        if content.strip() and not mapping.get("tool_calls"):
                            final_ai_idx = chunk_index

            _log(
                "S1-TOOL Step 2 结果: "
                f"seen_to_upper={seen_to_upper}, request_idx={request_idx}, "
                f"result_idx={result_idx}, final_ai_idx={final_ai_idx}"
            )

            assert seen_to_upper, "未观测到 to_upper 工具调用"
            assert request_idx is not None, "未观测到工具调用请求"
            assert result_idx is not None, "未观测到工具结果消息"
            assert final_ai_idx is not None, "未观测到最终 AI 输出"
            assert request_idx < result_idx <= final_ai_idx

            _log("S1-TOOL Step 3/3 校验通过")
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())
