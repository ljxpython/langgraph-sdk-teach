from __future__ import annotations

import argparse
import json
from typing import Any, Awaitable, Callable

from langgraph_sdk_learn_common import optional_metadata, pretty

Handler = Callable[[Any, argparse.Namespace], Awaitable[None]]


def register(subparsers: Any, add_runtime_args: Callable[[argparse.ArgumentParser], None]) -> dict[str, Handler]:
    create_thread = subparsers.add_parser("create-thread", help="创建 thread")
    add_runtime_args(create_thread)

    thread_count = subparsers.add_parser("thread-count", help="统计 threads")
    add_runtime_args(thread_count)
    thread_count.add_argument("--status", default=None, help="按状态过滤: idle/busy/interrupted/error")
    thread_count.add_argument("--metadata-graph-id", default=None, help="按 metadata.graph_id 过滤")

    thread_search = subparsers.add_parser("thread-search", help="检索 threads")
    add_runtime_args(thread_search)
    thread_search.add_argument("--status", default=None, help="按状态过滤: idle/busy/interrupted/error")
    thread_search.add_argument("--metadata-graph-id", default=None, help="按 metadata.graph_id 过滤")
    thread_search.add_argument("--limit", type=int, default=10, help="返回条数")
    thread_search.add_argument("--offset", type=int, default=0, help="偏移")

    thread_get = subparsers.add_parser("thread-get", help="获取 thread 详情")
    add_runtime_args(thread_get)
    thread_get.add_argument("--thread-id", required=True, help="目标 thread_id")

    thread_copy = subparsers.add_parser("thread-copy", help="复制 thread")
    add_runtime_args(thread_copy)
    thread_copy.add_argument("--thread-id", required=True, help="目标 thread_id")

    thread_update = subparsers.add_parser("thread-update", help="更新 thread metadata")
    add_runtime_args(thread_update)
    thread_update.add_argument("--thread-id", required=True, help="目标 thread_id")
    thread_update.add_argument("--metadata-json", required=True, help='metadata JSON 字符串，例如 {"user_id":"u1"}')

    thread_delete = subparsers.add_parser("thread-delete", help="删除 thread")
    add_runtime_args(thread_delete)
    thread_delete.add_argument("--thread-id", required=True, help="目标 thread_id")

    state = subparsers.add_parser("state", help="查看 thread state")
    add_runtime_args(state)
    state.add_argument("--thread-id", required=True, help="目标 thread_id")

    history = subparsers.add_parser("history", help="查看 thread history")
    add_runtime_args(history)
    history.add_argument("--thread-id", required=True, help="目标 thread_id")
    history.add_argument("--limit", type=int, default=10, help="返回条数")

    return {
        "create-thread": handle_create_thread,
        "thread-count": handle_thread_count,
        "thread-search": handle_thread_search,
        "thread-get": handle_thread_get,
        "thread-copy": handle_thread_copy,
        "thread-update": handle_thread_update,
        "thread-delete": handle_thread_delete,
        "state": handle_state,
        "history": handle_history,
    }


async def handle_create_thread(client: Any, _: argparse.Namespace) -> None:
    # 对应 cURL: POST /threads
    # 作用: 创建 thread（会话状态容器）。
    # 主要参数: metadata/thread_id/if_exists/supersteps/graph_id/ttl（此处用最小调用）。
    result = await client.threads.create()
    print(pretty(result))


async def handle_thread_count(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /threads/count
    # 作用: 统计线程数量。
    # 主要参数: status, metadata。
    result = await client.threads.count(status=args.status, metadata=optional_metadata(args.metadata_graph_id))
    print(pretty({"count": result}))


async def handle_thread_search(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /threads/search
    # 作用: 检索线程列表。
    # 主要参数: status/metadata/limit/offset。
    result = await client.threads.search(
        status=args.status,
        metadata=optional_metadata(args.metadata_graph_id),
        limit=args.limit,
        offset=args.offset,
    )
    print(pretty(result))


async def handle_thread_get(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}
    # 作用: 获取 thread 元信息。
    # 主要参数: thread_id。
    result = await client.threads.get(args.thread_id)
    print(pretty(result))


async def handle_thread_copy(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /threads/{thread_id}/copy
    # 作用: 复制 thread，常用于 A/B 对照实验。
    # 主要参数: thread_id。
    result = await client.threads.copy(args.thread_id)
    print(pretty(result))


async def handle_thread_update(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: PATCH /threads/{thread_id}
    # 作用: 更新 thread metadata/ttl。
    # 主要参数: thread_id, metadata。
    metadata = json.loads(args.metadata_json)
    if not isinstance(metadata, dict):
        raise ValueError("--metadata-json 必须是 JSON 对象")
    result = await client.threads.update(args.thread_id, metadata=metadata)
    print(pretty(result))


async def handle_thread_delete(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: DELETE /threads/{thread_id}
    # 作用: 删除 thread。
    # 主要参数: thread_id。
    await client.threads.delete(args.thread_id)
    print(pretty({"deleted": args.thread_id}))


async def handle_state(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}/state
    # 作用: 查看当前状态快照。
    # 主要参数: thread_id（可选 checkpoint_id 在 REST 中可用）。
    result = await client.threads.get_state(args.thread_id)
    print(pretty(result))


async def handle_history(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET/POST /threads/{thread_id}/history
    # 作用: 查看历史状态快照序列。
    # 主要参数: thread_id, limit。
    result = await client.threads.get_history(args.thread_id, limit=args.limit)
    print(pretty(result))
