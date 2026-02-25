from __future__ import annotations

from typing import TypedDict


class AssistantAgentContext(TypedDict, total=False):
    environment: str
    model_id: str
    system_prompt: str
