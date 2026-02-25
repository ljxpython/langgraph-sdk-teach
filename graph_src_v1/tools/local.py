from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool


@tool(description="Count words in text.")
def word_count(text: str) -> int:
    return len([w for w in text.split() if w.strip()])


@tool(description="Get current UTC timestamp.")
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@tool(description="Convert text to uppercase.")
def to_upper(text: str) -> str:
    return text.upper()


def get_local_tools() -> list[Any]:
    return [word_count, utc_now, to_upper]
