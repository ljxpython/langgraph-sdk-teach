from __future__ import annotations

from typing import Any

from graph_src_v2.runtime.options import AppRuntimeConfig
from graph_src_v2.tools.registry import build_tools


async def build_assistant_tools(options: AppRuntimeConfig) -> list[Any]:
    return await build_tools(options)
