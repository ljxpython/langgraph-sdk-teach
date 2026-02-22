from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Mapping, cast

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _last_ai_content(run_result: Any) -> str:
    messages = _as_mapping(run_result).get("messages", [])
    for message in reversed(messages):
        if message.get("type") == "ai":
            return str(message.get("content", ""))
    return ""


def _log(message: str) -> None:
    print(f"[E2E] {message}")


def test_create_assistant_thread_run_override_get_cleanup() -> None:
    # ==================== 测试目标 ====================
    # 验证完整链路：创建 assistant -> 创建 thread -> 默认运行 -> run 临时覆盖 -> 回读校验 -> 清理
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    graph_id = os.getenv("LANGGRAPH_GRAPH_ID", "agent")
    recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "60"))
    _log(
        f"准备执行全链路测试: url={url}, graph_id={graph_id}, recursion_limit={recursion_limit}"
    )

    async def _run_flow() -> None:
        client = get_client(url=url)
        assistant_id: str | None = None
        thread_id: str | None = None

        # 使用唯一名称，避免和历史测试数据冲突。
        unique_name = f"assistant-e2e-{uuid.uuid4().hex[:8]}"
        default_prompt = "你是默认角色"
        override_prompt = "你是一次性覆盖角色"

        try:
            # Step 1: 创建 assistant（持久化默认 context）。
            _log("Step 1/6 创建 assistant（写入默认 context）")
            assistant = await client.assistants.create(
                graph_id,
                name=unique_name,
                context={
                    "model_provider": "glm4",
                    "system_prompt": default_prompt,
                },
            )
            assistant_id = assistant["assistant_id"]
            _log(f"Step 1 校验通过: assistant_id={assistant_id}, name={unique_name}")

            # Step 2: 创建 thread（会话容器）。
            _log("Step 2/6 创建 thread（会话容器）")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]
            _log(f"Step 2 校验通过: thread_id={thread_id}")

            # Step 3: 默认运行（不传 run 级覆盖，验证可正常执行）。
            _log("Step 3/6 默认运行（不传 run 级覆盖）")
            default_result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "你好，请只回复ok"}]},
                config={"recursion_limit": recursion_limit},
            )
            default_content = _last_ai_content(default_result)
            _log(f"Step 3 输出: {default_content}")
            assert "ok" in default_content.lower()
            _log("Step 3 校验通过: 默认运行返回包含 ok")

            # Step 4: run 临时覆盖（只影响本次执行）。
            _log("Step 4/6 run 临时覆盖 system_prompt（仅本次有效）")
            override_result = await client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "说明你当前角色"}]},
                context={"system_prompt": override_prompt},
                config={"recursion_limit": recursion_limit},
            )
            override_content = _last_ai_content(override_result)
            _log(f"Step 4 输出: {override_content}")
            assert "覆盖角色" in override_content
            _log("Step 4 校验通过: 本次 run 已体现临时覆盖角色")

            # Step 5: 回读 assistant，确认 run 覆盖没有写回默认 context。
            _log("Step 5/6 回读 assistant 配置，确认未被 run 覆盖污染")
            assistant_latest = _as_mapping(await client.assistants.get(assistant_id))
            context = _as_mapping(assistant_latest.get("context"))
            latest_prompt = cast(str, context.get("system_prompt"))
            _log(f"Step 5 读取到 assistant.context.system_prompt={latest_prompt}")
            assert latest_prompt == default_prompt
            _log("Step 5 校验通过: assistant 默认配置未被 run 临时覆盖写回")

        finally:
            # Step 6: 清理测试数据，防止污染环境。
            _log("Step 6/6 清理资源（assistant, thread）")
            if assistant_id is not None:
                await client.assistants.delete(assistant_id, delete_threads=False)
                _log(f"Step 6 删除 assistant 完成: {assistant_id}")
            if thread_id is not None:
                await client.threads.delete(thread_id)
                _log(f"Step 6 删除 thread 完成: {thread_id}")

    _log("开始执行 asyncio 测试流程")
    asyncio.run(_run_flow())
    _log("全链路测试完成: 所有校验步骤通过")
