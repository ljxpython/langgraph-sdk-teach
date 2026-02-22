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


def _state_texts(state: Any) -> list[str]:
    values = _as_mapping(state).get("values", {})
    messages = _as_mapping(values).get("messages", [])
    return [str(_as_mapping(msg).get("content", "")) for msg in messages]


def _iter_mappings(value: Any):
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _iter_mappings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_mappings(item)


def _supports_kwarg(func: Any, kwarg: str) -> bool:
    try:
        return kwarg in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def _classify_tool_source(tool_name: str, local_tools: set[str], mcp_tools: set[str]) -> str:
    if tool_name == "write_todos":
        return "deepagent_todo"
    if tool_name in {"ls", "read_file", "write_file", "edit_file", "glob", "grep"}:
        return "deepagent_fs"
    if tool_name in local_tools:
        return "local_tool"
    if tool_name in mcp_tools:
        return "mcp_tool"
    if tool_name == "task":
        return "deepagent_subagent"
    return "unknown_tool"


def _normalize_hitl_interrupt(result: Mapping[str, Any]) -> dict[str, Any]:
    interrupts = result.get("__interrupt__")
    if not isinstance(interrupts, list) or not interrupts:
        return {"interrupted": False, "action_requests": []}

    first = interrupts[0]
    first_map = first if isinstance(first, Mapping) else {}
    value = first_map.get("value") if isinstance(first_map.get("value"), Mapping) else getattr(first, "value", None)
    payload = value if isinstance(value, Mapping) else {}
    action_requests = payload.get("action_requests")
    if not isinstance(action_requests, list):
        action_requests = []

    normalized: list[dict[str, Any]] = []
    for req in action_requests:
        req_map = req if isinstance(req, Mapping) else {}
        normalized.append({"tool_name": str(req_map.get("name", "")), "args": req_map.get("args")})

    return {"interrupted": True, "action_requests": normalized}


def _log(message: str) -> None:
    print(f"[STREAM-S4] {message}")


def _interrupt_action_tool_names(run_result: Mapping[str, Any]) -> list[str]:
    interrupts = run_result.get("__interrupt__")
    if not isinstance(interrupts, list) or not interrupts:
        return []
    first = interrupts[0]
    first_map = first if isinstance(first, Mapping) else {}
    value = first_map.get("value")
    value_map = value if isinstance(value, Mapping) else {}
    reqs = value_map.get("action_requests")
    if not isinstance(reqs, list):
        return []
    return [str(_as_mapping(req).get("name", "")) for req in reqs]


def _message_tool_observation(run_result: Mapping[str, Any]) -> tuple[bool, bool]:
    messages = run_result.get("messages")
    if not isinstance(messages, list):
        return False, False
    seen_task_call = False
    seen_task_tool_result = False
    for msg in messages:
        mapping = _as_mapping(msg)
        tool_calls = mapping.get("tool_calls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if str(_as_mapping(tc).get("name", "")) == "task":
                    seen_task_call = True
        if str(mapping.get("type", "")) == "tool" and str(mapping.get("name", "")) == "task":
            seen_task_tool_result = True
    return seen_task_call, seen_task_tool_result


def test_streaming_stage_s4_unified_chain_and_join_boundary() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            _log("S4-CHAIN Step 1/5 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            user_query = (
                "你必须调用名为 to_upper 的工具, 参数 text='hello world'。"
                "禁止直接给出答案, 必须先调用工具, 最后仅输出工具结果。"
            )
            context = {
                "enable_local_tools": True,
                "enable_local_mcp": False,
                "system_prompt": "你必须严格按用户要求先调用工具再作答。",
            }

            _log("S4-CHAIN Step 2/5 自然语言输入并流式采集")
            request_idx: int | None = None
            result_idx: int | None = None
            final_ai_idx: int | None = None
            seen_messages_event = False
            seen_to_upper = False
            chunk_index = 0

            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": user_query}]},
                context=context,
                stream_mode=["updates", "messages", "tasks", "debug"],
            ):
                chunk_index += 1
                event_name = str(getattr(chunk, "event", ""))
                if event_name.startswith("messages"):
                    seen_messages_event = True

                for mapping in _iter_mappings(getattr(chunk, "data", None)):
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
                "S4-CHAIN Step 2 结果: "
                f"seen_messages_event={seen_messages_event}, seen_to_upper={seen_to_upper}, "
                f"request_idx={request_idx}, result_idx={result_idx}, final_ai_idx={final_ai_idx}"
            )

            assert seen_messages_event
            assert seen_to_upper
            assert request_idx is not None and result_idx is not None and final_ai_idx is not None
            assert request_idx < result_idx <= final_ai_idx

            _log("S4-CHAIN Step 3/5 校验 user 输入已沉淀")
            state = await client.threads.get_state(thread_id)
            texts = _state_texts(state)
            assert any(user_query in text for text in texts)

            _log("S4-CHAIN Step 4/5 校验 join_stream 尾流边界")
            created = await client.runs.create(
                thread_id,
                assistant_id,
                input={
                    "messages": [
                        {
                            "role": "human",
                            "content": "请输出12条学习建议并给每条一句解释。",
                        }
                    ]
                },
            )
            run_id = _run_id_from(created)
            await asyncio.sleep(1.0)

            joined_events = 0
            async for _ in client.runs.join_stream(
                thread_id,
                run_id,
                stream_mode=["messages", "updates", "debug"],
            ):
                joined_events += 1

            _log(f"S4-CHAIN Step 4 结果: run_id={run_id}, joined_events={joined_events}")
            if joined_events == 0:
                _log("S4-CHAIN 说明: join_stream 无历史补发，0 事件属于允许边界")

            _log("S4-CHAIN Step 5/5 获取最终结果")
            joined_result = await client.runs.join(thread_id, run_id)
            final_text = _last_ai_content(joined_result)
            assert len(final_text.strip()) > 0
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_streaming_stage_s4_deepagent_todo_hitl_resume_contract() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_DEEPAGENT_ASSISTANT_ID", "deepagent_demo")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        local_tools = {"to_upper", "word_count", "utc_now"}
        mcp_tools = {"add", "multiply", "square", "reverse_text", "text_length"}
        supports_command = _supports_kwarg(client.runs.wait, "command")

        try:
            _log("S4-DEEP Step 1/4 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            _log("S4-DEEP Step 2/4 触发 deepagent ToDo + 子代理 + 文件写入")
            prompt = (
                "请先用todo列出三步计划，然后委托子代理完成一条研究结论，"
                "最后把结论写入 graph_src/demo_note.md。"
            )
            result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": prompt}]},
            )

            parsed = _normalize_hitl_interrupt(_as_mapping(result))
            interrupted = bool(parsed.get("interrupted"))
            action_requests = parsed.get("action_requests")
            requests = action_requests if isinstance(action_requests, list) else []
            tool_names = [str(_as_mapping(item).get("tool_name", "")) for item in requests]
            categories = [_classify_tool_source(name, local_tools, mcp_tools) for name in tool_names]
            _log(
                "S4-DEEP Step 2 结果: "
                f"interrupted={interrupted}, tool_names={tool_names}, categories={categories}"
            )

            if interrupted:
                assert len(requests) > 0
                assert "deepagent_todo" in categories

                if supports_command:
                    _log("S4-DEEP Step 3/4 批准中断动作并恢复")
                    decisions = [{"type": "approve"} for _ in requests]
                    resumed = await client.runs.wait(
                        thread_id,
                        assistant_id,
                        input=None,
                        command={"resume": {"decisions": decisions}},
                    )
                    resumed_text = _last_ai_content(resumed)
                    _log(f"S4-DEEP Step 3 恢复后输出长度: {len(resumed_text)}")
                    assert len(resumed_text.strip()) > 0 or len(_as_mapping(resumed)) > 0
                else:
                    _log("S4-DEEP Step 3 说明: 当前 SDK 未暴露 command 参数，保留中断可观测断言")
            else:
                _log("S4-DEEP Step 3 说明: 本次未触发中断，按兼容路径仅验证 run 可完成")
                text = _last_ai_content(result)
                assert len(text.strip()) > 0 or len(_as_mapping(result)) > 0

            _log("S4-DEEP Step 4/4 校验通过")
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_streaming_stage_s4_deepagent_subagent_delegate_and_tool_result() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_DEEPAGENT_ASSISTANT_ID", "deepagent_demo")
    supports_command = _supports_kwarg(get_client(url=url).runs.wait, "command")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        seen_interrupt_tools: list[str] = []

        try:
            _log("S4-SUBAGENT Step 1/5 创建 thread")
            thread = await client.threads.create()
            thread_id = _thread_id_from(thread)

            _log("S4-SUBAGENT Step 2/5 触发 write_todos -> task -> write_file")
            prompt = (
                "你必须严格按顺序执行三件事："
                "1)先调用 write_todos 写入3条任务；"
                "2)再调用 task 委托子智能体生成一条研究结论；"
                "3)最后调用 write_file 把结论写入 graph_src/demo_note.md。"
                "禁止跳步，禁止只给自然语言答案。"
            )
            result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": prompt}]},
            )

            _log("S4-SUBAGENT Step 3/5 处理中断并持续 approve 到完成")
            guard = 0
            while isinstance(_as_mapping(result).get("__interrupt__"), list) and _as_mapping(result).get("__interrupt__"):
                tools = _interrupt_action_tool_names(_as_mapping(result))
                seen_interrupt_tools.extend([name for name in tools if name])
                _log(f"S4-SUBAGENT 中断#{guard + 1}: tools={tools}")
                assert supports_command
                decisions = [{"type": "approve"} for _ in tools]
                result = await client.runs.wait(
                    thread_id,
                    assistant_id,
                    input=None,
                    command={"resume": {"decisions": decisions}},
                )
                guard += 1
                assert guard <= 20

            _log(f"S4-SUBAGENT Step 4/5 中断工具汇总: {seen_interrupt_tools}")
            assert "write_todos" in seen_interrupt_tools
            assert "task" in seen_interrupt_tools
            assert "write_file" in seen_interrupt_tools

            seen_task_call, seen_task_tool_result = _message_tool_observation(_as_mapping(result))
            _log(
                "S4-SUBAGENT Step 5/5 最终消息观测: "
                f"seen_task_call={seen_task_call}, seen_task_tool_result={seen_task_tool_result}"
            )
            assert seen_task_call
            assert seen_task_tool_result
        finally:
            if thread_id is not None:
                await client.threads.delete(thread_id)

    asyncio.run(_run())
