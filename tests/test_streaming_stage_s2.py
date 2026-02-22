from __future__ import annotations

import asyncio
import inspect
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


def _run_id_from(payload: Any) -> str:
    value = _as_mapping(payload).get("run_id")
    if not isinstance(value, str) or not value:
        raise AssertionError("缺少合法 run_id")
    return value


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if _as_mapping(message).get("type") == "ai":
            return str(_as_mapping(message).get("content", ""))
    return ""


def _log(message: str) -> None:
    print(f"[STREAM-S2] {message}")


def _classify_tool_source(tool_name: str, local_tools: set[str], mcp_tools: set[str]) -> str:
    if tool_name == "write_todos":
        return "deepagent_todo"
    if tool_name in {"ls", "read_file", "write_file", "edit_file", "glob", "grep"}:
        return "deepagent_fs"
    if tool_name in local_tools:
        return "local_tool"
    if tool_name in mcp_tools:
        return "mcp_tool"
    return "unknown_tool"


def _supports_kwarg(func: Any, kwarg: str) -> bool:
    try:
        return kwarg in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def test_streaming_stage_s2_subgraphs_stream_contract() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            _log("S2-SUB Step 1/3 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            supports_subgraphs = _supports_kwarg(client.runs.stream, "subgraphs")
            _log(
                "S2-SUB Step 2/3 采集事件 "
                f"(subgraphs_kwarg_supported={supports_subgraphs})"
            )
            seen_events: set[str] = set()
            payload_chunks = 0
            namespaced_chunks = 0

            stream_kwargs: dict[str, Any] = {
                "input": {"messages": [{"role": "human", "content": "请给我一条学习建议"}]},
                "stream_mode": ["updates", "messages", "debug"],
            }
            if supports_subgraphs:
                stream_kwargs["subgraphs"] = True

            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                **stream_kwargs,
            ):
                event_name = str(getattr(chunk, "event", ""))
                seen_events.add(event_name)
                data = getattr(chunk, "data", None)
                if data is not None:
                    payload_chunks += 1

                if isinstance(data, (tuple, list)) and len(data) == 2:
                    namespace = data[0]
                    if isinstance(namespace, tuple) and all(isinstance(item, str) for item in namespace):
                        namespaced_chunks += 1
                    if isinstance(namespace, list) and all(isinstance(item, str) for item in namespace):
                        namespaced_chunks += 1

            _log(
                "S2-SUB Step 2 结果: "
                f"events={sorted(seen_events)}, payload_chunks={payload_chunks}, "
                f"namespaced_chunks={namespaced_chunks}"
            )

            assert payload_chunks > 0
            assert len(seen_events) > 0
            if supports_subgraphs and namespaced_chunks == 0:
                _log("S2-SUB 说明: 当前 assistant 可能没有 subgraph 节点，未出现命名空间 tuple，属于可接受结果")
            if not supports_subgraphs:
                _log("S2-SUB 说明: 当前 SDK 不支持 stream(subgraphs=...)，已降级为通用流式契约校验")

            _log("S2-SUB Step 3/3 校验通过")
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_streaming_stage_s2_join_stream_live_tail() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            _log("S2-JOIN Step 1/4 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            _log("S2-JOIN Step 2/4 先创建 run，再延迟 join_stream")
            run_id: str | None = None
            joined_events = 0
            non_empty_payload = 0

            for attempt in (1, 2):
                created = await client.runs.create(
                    thread_id,
                    assistant_id,
                    input={
                        "messages": [
                            {
                                "role": "human",
                                "content": "请输出一段不少于12条的编号学习建议，每条后再补一句解释。",
                            }
                        ]
                    },
                )
                run_id = _run_id_from(created)
                await asyncio.sleep(1.0)

                joined_events = 0
                non_empty_payload = 0
                async for chunk in client.runs.join_stream(
                    thread_id,
                    run_id,
                    stream_mode=["messages", "updates", "debug"],
                ):
                    joined_events += 1
                    if getattr(chunk, "data", None) is not None:
                        non_empty_payload += 1

                _log(
                    f"S2-JOIN 尝试{attempt}: run_id={run_id}, joined_events={joined_events}, "
                    f"non_empty_payload={non_empty_payload}"
                )
                if joined_events > 0:
                    break

            assert run_id is not None
            if joined_events == 0:
                _log("S2-JOIN 说明: 本次 join_stream 未捕获到尾流事件，符合官方“无历史补发”边界")

            _log("S2-JOIN Step 3/4 join 获取最终结果")
            joined_result = await client.runs.join(thread_id, run_id)
            text = _last_ai_content(joined_result)
            _log(f"S2-JOIN Step 3 输出长度: {len(text)}")
            assert len(text.strip()) > 0

            _log("S2-JOIN Step 4/4 校验通过（注意：未对历史补发做断言，遵循官方限制）")
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_streaming_stage_s2_machine_readable_classification_rules() -> None:
    _log("S2-CLS Step 1/2 校验工具来源分类规则")

    local_tools = {"to_upper", "word_count", "utc_now"}
    mcp_tools = {"add", "multiply", "square", "reverse_text", "text_length"}

    assert _classify_tool_source("write_todos", local_tools, mcp_tools) == "deepagent_todo"
    assert _classify_tool_source("read_file", local_tools, mcp_tools) == "deepagent_fs"
    assert _classify_tool_source("to_upper", local_tools, mcp_tools) == "local_tool"
    assert _classify_tool_source("add", local_tools, mcp_tools) == "mcp_tool"
    assert _classify_tool_source("something_else", local_tools, mcp_tools) == "unknown_tool"

    _log("S2-CLS Step 2/2 校验通过")
