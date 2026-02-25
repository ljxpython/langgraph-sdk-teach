from __future__ import annotations

from typing import TypedDict


class DeepAgentContext(TypedDict, total=False):
    environment: str
    model_id: str
    system_prompt: str
    temperature: float
    max_tokens: int
    top_p: float
    enable_local_tools: bool
    enable_local_mcp: bool
    mcp_servers: list[str]
    skills: list[str]
    subagents: list[dict[str, object]]
