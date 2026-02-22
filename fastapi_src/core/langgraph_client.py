from __future__ import annotations

from langgraph_sdk import get_client


def get_langgraph_client(api_url: str):
    return get_client(url=api_url)
