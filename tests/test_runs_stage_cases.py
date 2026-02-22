from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Mapping

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if _as_mapping(message).get("type") == "ai":
            return str(_as_mapping(message).get("content", ""))
    return ""


def _message_texts(state: Any) -> list[str]:
    values = _as_mapping(state).get("values", {})
    messages = _as_mapping(values).get("messages", [])
    return [str(_as_mapping(msg).get("content", "")) for msg in messages]


def _log(message: str) -> None:
    print(f"[RUN-STAGE-CASE] {message}")


def _env() -> tuple[str, str, int]:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))
    return url, assistant_id, recursion_limit


def test_stage_r1_stateful_wait_and_stream() -> None:
    # ==================== Stage R1 ====================
    # 验证点：
    # 1) 在有 thread 的前提下，wait 能拿到最终结果
    # 2) stream 能持续输出事件流
    url, assistant_id, recursion_limit = _env()

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        try:
            _log("R1-1 创建 thread")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]
            _log(f"R1-1 完成: thread_id={thread_id}")

            _log("R1-2 执行 runs.wait（stateful）")
            wait_result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "你好，请只回复ok"}]},
                config={"recursion_limit": recursion_limit},
            )
            wait_text = _last_ai_content(wait_result)
            _log(f"R1-2 输出: {wait_text}")
            assert "ok" in wait_text.lower()

            _log("R1-3 执行 runs.stream（stateful）")
            has_event_payload = False
            async for chunk in client.runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "请给我两条建议"}]},
                config={"recursion_limit": recursion_limit},
                stream_mode=["updates", "messages"],
            ):
                if chunk.data and isinstance(chunk.data, Mapping):
                    has_event_payload = True
                    break
            _log(f"R1-3 校验: has_event_payload={has_event_payload}")
            assert has_event_payload
        finally:
            if thread_id is not None:
                _log(f"R1-4 清理 thread={thread_id}")
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_stage_r2_background_run_lifecycle() -> None:
    # ==================== Stage R2 ====================
    # 验证点：create -> get/list -> join 生命周期
    url, assistant_id, recursion_limit = _env()

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        run_id: str | None = None
        try:
            _log("R2-1 创建 thread")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]

            _log("R2-2 非阻塞创建 run")
            created = await client.runs.create(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "写3点总结"}]},
                config={"recursion_limit": recursion_limit},
            )
            run_id = _as_mapping(created).get("run_id")
            _log(f"R2-2 完成: run_id={run_id}")
            assert isinstance(run_id, str) and len(run_id) > 0

            _log("R2-3 读取 run 详情（get）")
            detail = await client.runs.get(thread_id, run_id)
            status_before = str(_as_mapping(detail).get("status", ""))
            _log(f"R2-3 状态: {status_before}")
            assert status_before in {"pending", "running", "success", "error", "timeout", "interrupted"}

            _log("R2-4 列表查询 runs（list）")
            runs = await client.runs.list(thread_id, limit=20, offset=0)
            run_ids = {str(_as_mapping(item).get("run_id", "")) for item in runs}
            _log(f"R2-4 命中数量: {len(run_ids)}")
            assert run_id in run_ids

            _log("R2-5 join 等待完成")
            await client.runs.join(thread_id, run_id)
            detail_after = await client.runs.get(thread_id, run_id)
            status_after = str(_as_mapping(detail_after).get("status", ""))
            _log(f"R2-5 最终状态: {status_after}")
            assert status_after == "success"
        finally:
            if thread_id is not None:
                _log(f"R2-6 清理 thread={thread_id}")
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_stage_r3_same_thread_two_assistants() -> None:
    # ==================== Stage R3 ====================
    # 验证点：同一 thread 上切换 assistant，历史消息仍由 thread 继续承载
    url, default_assistant_id, recursion_limit = _env()

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        assistant_a_id: str | None = None
        name = f"same-thread-a-{uuid.uuid4().hex[:8]}"
        first_prompt = "请记住我的名字是小王，并回复“记住了”"
        second_prompt = "我刚刚说我的名字是什么？"

        try:
            _log("R3-1 创建 assistant A（自定义角色）")
            assistant_a = await client.assistants.create(
                "agent",
                name=name,
                context={"system_prompt": "你是A角色"},
            )
            assistant_a_id = assistant_a["assistant_id"]
            _log(f"R3-1 完成: assistant_a_id={assistant_a_id}")

            _log("R3-2 创建 thread")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]

            _log("R3-3 用 assistant A 在同一 thread 执行第1轮")
            first_run = await client.runs.wait(
                thread_id,
                assistant_a_id,
                input={"messages": [{"role": "human", "content": first_prompt}]},
                config={"recursion_limit": recursion_limit},
            )
            _log(f"R3-3 输出: {_last_ai_content(first_run)}")

            _log("R3-4 切换默认 assistant，在同一 thread 执行第2轮")
            second_run = await client.runs.wait(
                thread_id,
                default_assistant_id,
                input={"messages": [{"role": "human", "content": second_prompt}]},
                config={"recursion_limit": recursion_limit},
            )
            second_text = _last_ai_content(second_run)
            _log(f"R3-4 输出: {second_text}")
            assert len(second_text) > 0

            _log("R3-5 回读 thread state，验证两轮问题都在同一线程历史中")
            state = await client.threads.get_state(thread_id)
            texts = _message_texts(state)
            assert any(first_prompt in text for text in texts)
            assert any(second_prompt in text for text in texts)
            _log("R3-5 校验通过: 同一 thread 持续承载上下文")
        finally:
            if assistant_a_id is not None:
                _log(f"R3-6 清理 assistant={assistant_a_id}")
                await client.assistants.delete(assistant_a_id, delete_threads=False)
            if thread_id is not None:
                _log(f"R3-6 清理 thread={thread_id}")
                await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_stage_r4_stateless_wait_and_stream() -> None:
    # ==================== Stage R4 ====================
    # 验证点：不传 thread_id（None）时可执行无状态 wait/stream
    url, assistant_id, recursion_limit = _env()

    async def _run() -> None:
        client = get_client(url=url)

        _log("R4-1 无状态 runs.wait")
        wait_result = await client.runs.wait(
            None,
            assistant_id,
            input={"messages": [{"role": "human", "content": "只用一句话介绍你自己"}]},
            config={"recursion_limit": recursion_limit},
        )
        wait_text = _last_ai_content(wait_result)
        _log(f"R4-1 输出: {wait_text}")
        assert len(wait_text) > 0

        _log("R4-2 无状态 runs.stream")
        got_payload = False
        async for chunk in client.runs.stream(
            None,
            assistant_id,
            input={"messages": [{"role": "human", "content": "给我两条建议"}]},
            config={"recursion_limit": recursion_limit},
            stream_mode=["updates"],
        ):
            if chunk.data and isinstance(chunk.data, Mapping) and "run_id" not in chunk.data:
                got_payload = True
                break
        _log(f"R4-2 校验: got_payload={got_payload}")
        assert got_payload

    asyncio.run(_run())


def test_stage_r5_cron_create_and_cleanup() -> None:
    # ==================== Stage R5 ====================
    # 验证点：
    # 1) create_for_thread 与 create（stateless）都能创建 cron
    # 2) cron 表达式按 UTC 解释（此处仅做创建，不等待触发）
    # 3) 测试结束必须删除 cron，避免持续产生费用
    url, assistant_id, _ = _env()

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        cron_thread_id: str | None = None
        cron_stateless_id: str | None = None

        try:
            _log("R5-1 创建 thread（用于 create_for_thread）")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]

            _log("R5-2 创建 thread-bound cron")
            cron_for_thread = await client.crons.create_for_thread(
                thread_id,
                assistant_id,
                schedule="*/30 * * * *",
                input={"messages": [{"role": "user", "content": "What time is it?"}]},
            )
            cron_thread_id = str(_as_mapping(cron_for_thread).get("cron_id", ""))
            _log(f"R5-2 完成: cron_id={cron_thread_id}")
            assert len(cron_thread_id) > 0

            _log("R5-3 创建 stateless cron")
            cron_stateless = await client.crons.create(
                assistant_id,
                schedule="*/30 * * * *",
                input={"messages": [{"role": "user", "content": "Daily report"}]},
                on_run_completed="delete",
            )
            cron_stateless_id = str(_as_mapping(cron_stateless).get("cron_id", ""))
            _log(f"R5-3 完成: cron_id={cron_stateless_id}")
            assert len(cron_stateless_id) > 0
        finally:
            if cron_thread_id:
                _log(f"R5-4 删除 thread-bound cron={cron_thread_id}")
                await client.crons.delete(cron_thread_id)
            if cron_stateless_id:
                _log(f"R5-4 删除 stateless cron={cron_stateless_id}")
                await client.crons.delete(cron_stateless_id)
            if thread_id is not None:
                _log(f"R5-4 清理 thread={thread_id}")
                await client.threads.delete(thread_id)

    asyncio.run(_run())
