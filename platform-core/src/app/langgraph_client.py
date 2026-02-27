from __future__ import annotations

from langgraph_sdk import get_client

from src.app.config import get_upstream_url


def build_langgraph_client():
    return get_client(url=get_upstream_url())
