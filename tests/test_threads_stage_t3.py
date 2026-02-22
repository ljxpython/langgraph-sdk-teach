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
    texts: list[str] = []
    for item in messages:
        texts.append(str(_as_mapping(item).get("content", "")))
    return texts


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if _as_mapping(message).get("type") == "ai":
            return str(_as_mapping(message).get("content", ""))
    return ""


def _ai_message_count(run_result: Any) -> int:
    messages = _as_mapping(run_result).get("messages", [])
    count = 0
    for message in messages:
        if _as_mapping(message).get("type") == "ai":
            count += 1
    return count


def _log(message: str) -> None:
    print(f"[THREAD-T3] {message}")


def _thread_id_from(payload: Any, field_name: str) -> str:
    value = _as_mapping(payload).get("thread_id")
    if not isinstance(value, str) or not value:
        raise AssertionError(f"{field_name} 缺少合法 thread_id")
    return value


def test_threads_stage_t3_copy_ab_experiment() -> None:
    # ==================== Stage T3 测试目标 ====================
    # 验证完整链路：基线 thread -> thread-copy 出 A/B -> 单变量对比运行 -> state/history 对照 -> 清理
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))

    baseline_text = "请记住：项目主题是 LangGraph SDK 学习。"
    query_text = "给出今天学习计划"

    async def _run() -> None:
        client = get_client(url=url)
        base_thread_id: str | None = None
        thread_a_id: str | None = None
        thread_b_id: str | None = None

        try:
            # Step 1: 创建基线 thread 并写入相同起始上下文
            _log("Step 1/8 创建基线 thread")
            base = await client.threads.create()
            base_thread_id = _thread_id_from(base, "base thread")
            _log(f"Step 1 完成: base_thread_id={base_thread_id}")

            _log("Step 2/8 向基线 thread 写入起始上下文")
            await client.runs.wait(
                base_thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": baseline_text}]},
                config={"recursion_limit": recursion_limit},
            )
            _log("Step 2 完成: 基线上下文已写入")

            # Step 3: 复制出 A/B 两个分支线程
            _log("Step 3/8 复制 thread A")
            copy_a = await client.threads.copy(base_thread_id)
            thread_a_id = _thread_id_from(copy_a, "thread A")
            _log(f"Step 3 完成: thread_a_id={thread_a_id}")

            _log("Step 4/8 复制 thread B")
            copy_b = await client.threads.copy(base_thread_id)
            thread_b_id = _thread_id_from(copy_b, "thread B")
            _log(f"Step 4 完成: thread_b_id={thread_b_id}")

            # Step 4.5: 校验 A/B 起点都包含同一基线信息
            _log("Step 5/8 校验 A/B 都继承了相同基线上下文")
            state_a_before = await client.threads.get_state(thread_a_id)
            state_b_before = await client.threads.get_state(thread_b_id)
            texts_a_before = _message_texts_from_state(state_a_before)
            texts_b_before = _message_texts_from_state(state_b_before)
            assert any(baseline_text in text for text in texts_a_before)
            assert any(baseline_text in text for text in texts_b_before)
            _log("Step 5 校验通过: A/B 起点一致")

            # Step 6: A/B 只改一个变量（system_prompt）
            _log("Step 6/8 运行 A 组（简洁提示词）")
            run_a = await client.runs.wait(
                thread_a_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": query_text}]},
                context={"system_prompt": "请只给3条简洁要点"},
                config={"recursion_limit": recursion_limit},
            )
            out_a = _last_ai_content(run_a)
            _log(f"Step 6 A组输出: {out_a}")
            assert _ai_message_count(run_a) >= 1

            _log("Step 7/8 运行 B 组（详细提示词）")
            run_b = await client.runs.wait(
                thread_b_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": query_text}]},
                context={"system_prompt": "请给分阶段详细计划并给验收标准"},
                config={"recursion_limit": recursion_limit},
            )
            out_b = _last_ai_content(run_b)
            _log(f"Step 7 B组输出: {out_b}")
            assert _ai_message_count(run_b) >= 1

            # Step 7.5: 用 state/history 验证两组都完成了独立演进
            _log("Step 8/8 对比 A/B 的 state 与 history")
            state_a_after = await client.threads.get_state(thread_a_id)
            state_b_after = await client.threads.get_state(thread_b_id)
            texts_a_after = _message_texts_from_state(state_a_after)
            texts_b_after = _message_texts_from_state(state_b_after)
            assert any(query_text in text for text in texts_a_after)
            assert any(query_text in text for text in texts_b_after)

            hist_a = await client.threads.get_history(thread_a_id, limit=10)
            hist_b = await client.threads.get_history(thread_b_id, limit=10)
            _log(f"Step 8 history 条数: A={len(hist_a)}, B={len(hist_b)}")
            assert len(hist_a) >= 1
            assert len(hist_b) >= 1
            _log("Step 8 校验通过: A/B 独立演进完成")

        finally:
            # Step 9: 清理资源，防止学习环境污染
            _log("清理阶段: 删除临时 threads")
            if thread_a_id is not None:
                await client.threads.delete(thread_a_id)
                _log(f"已删除 thread_a={thread_a_id}")
            if thread_b_id is not None:
                await client.threads.delete(thread_b_id)
                _log(f"已删除 thread_b={thread_b_id}")
            if base_thread_id is not None:
                await client.threads.delete(base_thread_id)
                _log(f"已删除 base_thread={base_thread_id}")

    _log("开始执行 Threads Stage T3 自动化测试")
    asyncio.run(_run())
    _log("Threads Stage T3 自动化测试完成")
