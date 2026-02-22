from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Mapping

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _thread_id_from(payload: Any) -> str:
    value = _as_mapping(payload).get("thread_id")
    if not isinstance(value, str) or not value:
        raise AssertionError("缺少合法 thread_id")
    return value


def _log(message: str) -> None:
    print(f"[THREAD-T4] {message}")


def test_threads_stage_t4_lifecycle_governance() -> None:
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        tag = f"t4-{uuid.uuid4().hex[:8]}"

        _log("Step 1/4 创建治理目标 thread")
        thread = await client.threads.create()
        thread_id = _thread_id_from(thread)
        _log(f"Step 1 完成: thread_id={thread_id}")

        _log("Step 2/4 更新 metadata 做治理标记")
        metadata = {"cleanup_batch": tag, "owner": "learn", "scene": "ab-test", "graph_id": "agent"}
        updated = await client.threads.update(thread_id, metadata=metadata)
        updated_meta = _as_mapping(_as_mapping(updated).get("metadata", {}))
        assert updated_meta.get("cleanup_batch") == tag
        _log(f"Step 2 完成: metadata={updated_meta}")

        _log("Step 3/4 清理前盘点（search/count）")
        searched = await client.threads.search(status="idle", metadata={"graph_id": "agent"}, limit=50, offset=0)
        ids = {str(_as_mapping(item).get("thread_id", "")) for item in searched}
        assert thread_id in ids
        counted = await client.threads.count(status="idle", metadata={"graph_id": "agent"})
        assert isinstance(counted, int) and counted >= 1
        _log(f"Step 3 完成: search_hits={len(ids)}, count={counted}")

        _log("Step 4/4 删除并复核不存在")
        await client.threads.delete(thread_id)
        _log(f"Step 4 删除完成: thread_id={thread_id}")
        thread_id = None

        deleted_ok = False
        try:
            await client.threads.get(_thread_id_from(thread))
        except Exception as exc:
            deleted_ok = True
            _log(f"Step 4 复核通过: get 已失败（{type(exc).__name__}）")
        assert deleted_ok

    _log("开始执行 Threads Stage T4 自动化测试")
    asyncio.run(_run())
    _log("Threads Stage T4 自动化测试完成")
