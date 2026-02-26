from __future__ import annotations

from typing import Any

from graph_src_v2.runtime.options import AppRuntimeConfig
from graph_src_v2.mcp.loader import get_mcp_tools
from graph_src_v2.tools.local import get_local_tools


async def build_tools(options: AppRuntimeConfig) -> list[Any]:
    tools: list[Any] = []
    if options.enable_local_tools:
        tools.extend(get_local_tools(options.local_tools))
    if options.enable_local_mcp:
        tools.extend(await get_mcp_tools(options.mcp_servers or []))
    return tools
