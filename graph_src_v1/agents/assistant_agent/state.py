from __future__ import annotations

from typing import TypedDict


class AssistantAgentContext(TypedDict, total=False):
    environment: str
    model_provider: str
    model_name: str
    model_base_url: str
    model_api_key: str
    system_prompt: str
