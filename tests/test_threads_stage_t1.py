from __future__ import annotations

import asyncio
import os
from typing import Any, Mapping

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _message_texts_from_state(state: Any) -> list[str]:
    values = _as_mapping(state).get("values", {})
    messages = _as_mapping(values).get("messages", [])
    result: list[str] = []
    for item in messages:
        result.append(str(_as_mapping(item).get("content", "")))
    return result


def _log(message: str) -> None:
    print(f"[THREAD-T1] {message}")


def test_threads_stage_t1_create_run_state_history() -> None:
    # ==================== Stage T1 测试目标 ====================
    # 验证完整链路：创建 thread -> 在该 thread 上执行 run -> 读取 state -> 读取 history -> 清理
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))
    user_text = "我叫小王，请记住我的名字"

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None

        try:
            # Step 1: 创建 thread
            _log("Step 1/5 创建 thread")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]
            _log(f"Step 1 校验通过: thread_id={thread_id}")

            # Step 2: 在该 thread 上执行一次 run
            _log("Step 2/5 执行 runs.wait（写入 thread 状态）")
            run_result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": user_text}]},
                config={"recursion_limit": recursion_limit},
            )
            messages = _as_mapping(run_result).get("messages", [])
            _log(f"Step 2 输出消息条数: {len(messages)}")
            assert len(messages) >= 2

            # Step 3: 读取 state，验证消息已写入 thread
            _log("Step 3/5 读取 threads.get_state")
            state = await client.threads.get_state(thread_id)
            texts = _message_texts_from_state(state)
            _log(f"Step 3 读取到 messages 数量: {len(texts)}")
            assert any(user_text in text for text in texts)
            _log("Step 3 校验通过: 用户消息已写入 state")

            # Step 4: 读取 history，验证存在状态演进记录
            _log("Step 4/5 读取 threads.get_history")
            history = await client.threads.get_history(thread_id, limit=10)
            _log(f"Step 4 读取到 history 条数: {len(history)}")
            assert len(history) >= 1
            _log("Step 4 校验通过: history 中存在状态轨迹")

        finally:
            # Step 5: 清理 thread，避免污染学习环境
            _log("Step 5/5 清理资源")
            if thread_id is not None:
                await client.threads.delete(thread_id)
                _log(f"Step 5 删除 thread 完成: {thread_id}")

    _log("开始执行 Threads Stage T1 自动化测试")
    asyncio.run(_run())
    _log("Threads Stage T1 自动化测试完成")
