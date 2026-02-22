from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Mapping

from langgraph_sdk import get_client


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _log(message: str) -> None:
    print(f"[THREAD-T2] {message}")


def test_threads_stage_t2_metadata_search_count() -> None:
    # ==================== Stage T2 测试目标 ====================
    # 验证完整链路：创建 thread -> 更新 metadata -> 读取详情 -> 检索 -> 统计 -> 清理
    url = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123")

    async def _run() -> None:
        client = get_client(url=url)
        thread_id: str | None = None
        test_tag = f"t2-{uuid.uuid4().hex[:8]}"
        metadata = {
            "user_id": "u1",
            "biz": "demo",
            "tag": test_tag,
            "graph_id": "agent",
        }

        try:
            # Step 1: 创建 thread
            _log("Step 1/6 创建 thread")
            thread = await client.threads.create()
            thread_id = thread["thread_id"]
            _log(f"Step 1 校验通过: thread_id={thread_id}")

            # Step 2: 更新 metadata
            _log("Step 2/6 更新 thread metadata")
            updated = await client.threads.update(thread_id, metadata=metadata)
            updated_meta = _as_mapping(_as_mapping(updated).get("metadata", {}))
            _log(f"Step 2 读取 metadata: {updated_meta}")
            assert updated_meta.get("tag") == test_tag

            # Step 3: 读取 thread 详情，确认 metadata 落库
            _log("Step 3/6 读取 thread 详情确认 metadata")
            detail = await client.threads.get(thread_id)
            detail_meta = _as_mapping(_as_mapping(detail).get("metadata", {}))
            _log(f"Step 3 详情 metadata: {detail_meta}")
            assert detail_meta.get("tag") == test_tag

            # Step 4: 按 metadata.graph_id + status 检索
            _log("Step 4/6 检索 threads（status=idle, metadata.graph_id=agent）")
            items = await client.threads.search(
                status="idle",
                metadata={"graph_id": "agent"},
                limit=50,
                offset=0,
            )
            ids = {str(_as_mapping(item).get("thread_id", "")) for item in items}
            _log(f"Step 4 检索条数: {len(ids)}")
            assert thread_id in ids

            # Step 5: 统计数量（同筛选条件）
            _log("Step 5/6 统计 threads 数量（同筛选条件）")
            count = await client.threads.count(status="idle", metadata={"graph_id": "agent"})
            _log(f"Step 5 count={count}")
            assert isinstance(count, int)
            assert count >= 1

        finally:
            # Step 6: 清理 thread，防止污染环境
            _log("Step 6/6 清理资源")
            if thread_id is not None:
                await client.threads.delete(thread_id)
                _log(f"Step 6 删除 thread 完成: {thread_id}")

    _log("开始执行 Threads Stage T2 自动化测试")
    asyncio.run(_run())
    _log("Threads Stage T2 自动化测试完成")
