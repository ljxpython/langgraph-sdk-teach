from __future__ import annotations

import argparse
import json
from typing import Any, Awaitable, Callable

from langgraph_sdk_learn_common import pretty, resolve_assistant_uuid, target_assistant_id

Handler = Callable[[Any, argparse.Namespace], Awaitable[None]]


def register(subparsers: Any, add_runtime_args: Callable[[argparse.ArgumentParser], None]) -> dict[str, Handler]:
    assistants = subparsers.add_parser("assistants", help="列出 assistants")
    add_runtime_args(assistants)

    assistant_count = subparsers.add_parser("assistant-count", help="统计 assistants")
    add_runtime_args(assistant_count)

    assistant_get = subparsers.add_parser("assistant-get", help="获取 assistant 详情")
    add_runtime_args(assistant_get)
    assistant_get.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")

    assistant_schemas = subparsers.add_parser("assistant-schemas", help="获取 assistant schemas")
    add_runtime_args(assistant_schemas)
    assistant_schemas.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")

    assistant_graph = subparsers.add_parser("assistant-graph", help="获取 assistant graph")
    add_runtime_args(assistant_graph)
    assistant_graph.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_graph.add_argument("--xray", type=int, default=0, help="xray 参数")

    assistant_subgraphs = subparsers.add_parser("assistant-subgraphs", help="获取 assistant subgraphs")
    add_runtime_args(assistant_subgraphs)
    assistant_subgraphs.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_subgraphs.add_argument("--namespace", default=None, help="可选 namespace")
    assistant_subgraphs.add_argument("--recurse", action="store_true", help="是否递归")

    assistant_versions = subparsers.add_parser("assistant-versions", help="获取 assistant versions")
    add_runtime_args(assistant_versions)
    assistant_versions.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_versions.add_argument("--limit", type=int, default=10, help="返回条数")
    assistant_versions.add_argument("--offset", type=int, default=0, help="偏移")

    assistant_create = subparsers.add_parser("assistant-create", help="创建 assistant")
    add_runtime_args(assistant_create)
    assistant_create.add_argument("--graph-id", required=True, help="graph_id，例如 agent")
    assistant_create.add_argument("--name", default=None, help="assistant 名称")
    assistant_create.add_argument("--description", default=None, help="assistant 描述")
    assistant_create.add_argument("--config-json", default=None, help="assistant config JSON")
    assistant_create.add_argument("--context-json", default=None, help="assistant context JSON")
    assistant_create.add_argument("--metadata-json", default=None, help="assistant metadata JSON")

    assistant_update = subparsers.add_parser("assistant-update", help="更新 assistant")
    add_runtime_args(assistant_update)
    assistant_update.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_update.add_argument("--graph-id", default=None, help="可选：更新 graph_id")
    assistant_update.add_argument("--name", default=None, help="更新后的名称")
    assistant_update.add_argument("--description", default=None, help="更新后的描述")
    assistant_update.add_argument("--config-json", default=None, help="assistant config JSON")
    assistant_update.add_argument("--context-json", default=None, help="assistant context JSON")
    assistant_update.add_argument("--metadata-json", default=None, help="assistant metadata JSON")

    assistant_set_latest = subparsers.add_parser("assistant-set-latest", help="设置 assistant 最新版本")
    add_runtime_args(assistant_set_latest)
    assistant_set_latest.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_set_latest.add_argument("--version", type=int, required=True, help="版本号")

    assistant_delete = subparsers.add_parser("assistant-delete", help="删除 assistant")
    add_runtime_args(assistant_delete)
    assistant_delete.add_argument("--target-assistant-id", default=None, help="目标 assistant_id，不传则用全局 --assistant-id")
    assistant_delete.add_argument("--delete-threads", action="store_true", help="是否同时删除关联 threads")

    return {
        "assistants": handle_assistants,
        "assistant-count": handle_assistant_count,
        "assistant-get": handle_assistant_get,
        "assistant-schemas": handle_assistant_schemas,
        "assistant-graph": handle_assistant_graph,
        "assistant-subgraphs": handle_assistant_subgraphs,
        "assistant-versions": handle_assistant_versions,
        "assistant-create": handle_assistant_create,
        "assistant-update": handle_assistant_update,
        "assistant-set-latest": handle_assistant_set_latest,
        "assistant-delete": handle_assistant_delete,
    }


async def handle_assistants(client: Any, _: argparse.Namespace) -> None:
    # 对应 cURL: POST /assistants/search
    # 作用: 查询 assistant 列表。
    # 主要参数: graph_id/name/limit/offset（此处示例使用 limit/offset）。
    result = await client.assistants.search(limit=10, offset=0)
    print(pretty(result))


async def handle_assistant_count(client: Any, _: argparse.Namespace) -> None:
    # 对应 cURL: POST /assistants/count
    # 作用: 统计 assistant 数量。
    result = await client.assistants.count()
    print(pretty(result))


async def handle_assistant_get(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /assistants/{assistant_id}
    # 作用: 查看单个 assistant 详情。
    # 主要参数: assistant_id（可传 graph_id/name，脚本会先解析到 UUID）。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.get(assistant_id)
    print(pretty(result))


async def handle_assistant_schemas(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /assistants/{assistant_id}/schemas
    # 作用: 查看输入输出 schema。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.get_schemas(assistant_id)
    print(pretty(result))


async def handle_assistant_graph(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /assistants/{assistant_id}/graph
    # 作用: 查看图结构。
    # 主要参数: assistant_id, xray。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.get_graph(assistant_id, xray=args.xray)
    print(pretty(result))


async def handle_assistant_subgraphs(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /assistants/{assistant_id}/subgraphs
    # 作用: 查看子图结构。
    # 主要参数: assistant_id, namespace, recurse。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.get_subgraphs(assistant_id, namespace=args.namespace, recurse=args.recurse)
    print(pretty(result))


async def handle_assistant_versions(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /assistants/{assistant_id}/versions
    # 作用: 查看版本历史。
    # 主要参数: assistant_id, limit, offset。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.get_versions(assistant_id, limit=args.limit, offset=args.offset)
    print(pretty(result))


async def handle_assistant_create(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /assistants
    # 作用: 基于 graph_id 创建 assistant。
    # 主要参数: graph_id（必填），name/description（可选）。
    result = await client.assistants.create(
        args.graph_id,
        name=args.name,
        description=args.description,
        config=parse_json_field(args.config_json, "--config-json"),
        context=parse_json_field(args.context_json, "--context-json"),
        metadata=parse_json_field(args.metadata_json, "--metadata-json"),
    )
    print(pretty(result))


async def handle_assistant_update(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: PATCH /assistants/{assistant_id}
    # 作用: 更新 assistant 配置/元信息。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.update(
        assistant_id,
        graph_id=args.graph_id,
        name=args.name,
        description=args.description,
        config=parse_json_field(args.config_json, "--config-json"),
        context=parse_json_field(args.context_json, "--context-json"),
        metadata=parse_json_field(args.metadata_json, "--metadata-json"),
    )
    print(pretty(result))


async def handle_assistant_set_latest(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /assistants/{assistant_id}/latest
    # 作用: 切换最新版本。
    # 主要参数: assistant_id, version。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    result = await client.assistants.set_latest(assistant_id, args.version)
    print(pretty(result))


async def handle_assistant_delete(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: DELETE /assistants/{assistant_id}
    # 作用: 删除 assistant。
    # 主要参数: assistant_id, delete_threads。
    assistant_id = await resolve_assistant_uuid(client, target_assistant_id(args.target_assistant_id, args.assistant_id))
    await client.assistants.delete(assistant_id, delete_threads=args.delete_threads)
    print(pretty({"deleted": assistant_id, "delete_threads": args.delete_threads}))


def parse_json_field(raw: str | None, field: str) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} 不是合法 JSON") from exc
