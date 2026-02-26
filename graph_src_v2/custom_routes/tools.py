from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from graph_src_v2.mcp.servers import get_mcp_server_specs
from graph_src_v2.tools.local import get_local_tools

router = APIRouter(prefix="/internal/capabilities", tags=["capabilities"])


class ResolveRequest(BaseModel):
    enable_local_tools: bool | None = None
    local_tools: list[str] | str | None = None
    enable_local_mcp: bool | None = None
    mcp_servers: list[str] | str | None = None


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_name_list(raw: list[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        values = _split_csv(raw)
    else:
        values = [str(item).strip() for item in raw if str(item).strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _available_local_tools() -> dict[str, dict[str, str]]:
    available: dict[str, dict[str, str]] = {}
    for tool in get_local_tools(None):
        name = str(getattr(tool, "name", "")).strip().lower()
        if not name:
            continue
        description = str(getattr(tool, "description", "") or "")
        available[name] = {"name": name, "description": description}
    return available


@router.get("/tools")
def list_local_tools() -> dict[str, Any]:
    tools = sorted(_available_local_tools().values(), key=lambda item: item["name"])
    return {"count": len(tools), "tools": tools}


@router.get("/mcp-servers")
def list_mcp_servers() -> dict[str, Any]:
    specs = get_mcp_server_specs()
    servers: list[dict[str, Any]] = []
    for name in sorted(specs.keys()):
        spec = specs[name]
        servers.append(
            {
                "name": name,
                "transport": spec.get("transport"),
                "command": spec.get("command"),
                "args": list(spec.get("args") or []),
            }
        )
    return {"count": len(servers), "servers": servers}


@router.post("/resolve")
def resolve_capabilities(payload: ResolveRequest) -> dict[str, Any]:
    local_catalog = _available_local_tools()
    mcp_catalog = get_mcp_server_specs()

    enable_local_tools = bool(payload.enable_local_tools)
    enable_local_mcp = bool(payload.enable_local_mcp)

    selected_local_names = _normalize_name_list(payload.local_tools)
    selected_mcp_names = _normalize_name_list(payload.mcp_servers)

    if not enable_local_tools:
        selected_local_names = []
    elif not selected_local_names:
        selected_local_names = sorted(local_catalog.keys())

    if not enable_local_mcp:
        selected_mcp_names = []

    unknown_tools = [name for name in selected_local_names if name not in local_catalog]
    if unknown_tools:
        allowed = ", ".join(sorted(local_catalog.keys()))
        raise HTTPException(status_code=400, detail=f"Unsupported local tools: {unknown_tools}. allowed: {allowed}")

    unknown_mcp = [name for name in selected_mcp_names if name not in mcp_catalog]
    if unknown_mcp:
        allowed = ", ".join(sorted(mcp_catalog.keys()))
        raise HTTPException(status_code=400, detail=f"Unsupported mcp servers: {unknown_mcp}. allowed: {allowed}")

    resolved_local_tools = [local_catalog[name] for name in selected_local_names]
    resolved_mcp_servers = [
        {
            "name": name,
            "transport": mcp_catalog[name].get("transport"),
            "command": mcp_catalog[name].get("command"),
            "args": list(mcp_catalog[name].get("args") or []),
        }
        for name in selected_mcp_names
    ]

    return {
        "enable_local_tools": enable_local_tools,
        "enable_local_mcp": enable_local_mcp,
        "local_tools": resolved_local_tools,
        "mcp_servers": resolved_mcp_servers,
    }
