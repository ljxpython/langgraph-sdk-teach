from __future__ import annotations

import json
import uuid
from typing import Any

DEFAULT_URL = "http://127.0.0.1:8123"
DEFAULT_ASSISTANT_ID = "agent"


def pretty(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def target_assistant_id(cli_target: str | None, fallback: str) -> str:
    return cli_target if cli_target else fallback


def optional_metadata(metadata_graph_id: str | None) -> dict[str, Any] | None:
    if not metadata_graph_id:
        return None
    return {"graph_id": metadata_graph_id}


def is_uuid_like(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


async def resolve_assistant_uuid(client: Any, value: str) -> str:
    if is_uuid_like(value):
        return value

    by_graph = await client.assistants.search(graph_id=value, limit=1, offset=0)
    if by_graph:
        resolved = by_graph[0]["assistant_id"]
        print(f"resolved assistant_id (from graph_id={value}): {resolved}")
        return resolved

    by_name = await client.assistants.search(name=value, limit=1, offset=0)
    if by_name:
        resolved = by_name[0]["assistant_id"]
        print(f"resolved assistant_id (from name={value}): {resolved}")
        return resolved

    raise ValueError(
        f"无法解析 assistant 标识: {value}. 请传 assistant UUID，或可匹配到的 graph_id/name。"
    )
