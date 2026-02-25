from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
from langgraph_sdk import get_client

from sdk_src.examples.langgraph_sdk_learn_common import build_client_headers


def _status_code(exc: Exception) -> int | None:
    direct = getattr(exc, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    cause = getattr(exc, "__cause__", None)
    cause_code = getattr(cause, "status_code", None)
    if isinstance(cause_code, int):
        return cause_code
    return None


def _client(token: str) -> Any:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")
    headers = build_client_headers(None, token)
    return get_client(url=url, headers=headers)


def test_owner_can_create_and_delete_thread() -> None:
    async def _run() -> None:
        client = _client("owner-token")
        thread = await client.threads.create()
        thread_id = thread["thread_id"]
        assert thread_id
        await client.threads.delete(thread_id)

    asyncio.run(_run())


def test_viewer_cannot_create_thread() -> None:
    async def _run() -> None:
        client = _client("viewer-token")
        try:
            await client.threads.create()
        except Exception as exc:  # noqa: BLE001
            code = _status_code(exc)
            assert code == 403
            return
        raise AssertionError("viewer should not be allowed to create thread")

    asyncio.run(_run())


def test_owner_thread_isolation_blocks_viewer_read() -> None:
    async def _run() -> None:
        owner_client = _client("owner-token")
        viewer_client = _client("viewer-token")
        thread = await owner_client.threads.create()
        thread_id = thread["thread_id"]
        try:
            try:
                await viewer_client.threads.get(thread_id)
            except Exception as exc:  # noqa: BLE001
                code = _status_code(exc)
                assert code in {403, 404}
                return
            raise AssertionError("viewer should not access owner thread")
        finally:
            await owner_client.threads.delete(thread_id)

    asyncio.run(_run())


def test_owner_can_run_assistant_with_sdk() -> None:
    openai_key = os.getenv("OPENAI_API_KEY")
    model_api_key = os.getenv("MODEL_API_KEY")
    if not openai_key and not model_api_key:
        pytest.skip("No model API key configured for run execution test")

    async def _run() -> None:
        owner_client = _client("owner-token")
        assistant_id = os.getenv("LANGGRAPH_ASSISTANT_ID", "assistant")
        model_provider = os.getenv("MODEL_PROVIDER", "openai")
        model_name = os.getenv("MODEL_NAME", "gpt-4.1-mini")
        thread = await owner_client.threads.create()
        thread_id = thread["thread_id"]
        try:
            result = await owner_client.runs.wait(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": "请回复ok"}]},
                context={
                    "system_prompt": "请只输出ok",
                    "model_provider": model_provider,
                    "model_name": model_name,
                },
                config={"recursion_limit": 40},
            )
            assert isinstance(result, dict)
            assert result.get("messages")
        finally:
            await owner_client.threads.delete(thread_id)

    asyncio.run(_run())
