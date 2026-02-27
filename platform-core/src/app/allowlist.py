from __future__ import annotations

import re


_ALLOWED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("POST", re.compile(r"/assistants/search")),
    ("GET", re.compile(r"/assistants/[^/]+")),
    ("POST", re.compile(r"/threads")),
    ("POST", re.compile(r"/threads/search")),
    ("GET", re.compile(r"/threads/[^/]+")),
    ("POST", re.compile(r"/threads/[^/]+/runs/wait")),
    ("POST", re.compile(r"/threads/[^/]+/runs/stream")),
    ("POST", re.compile(r"/threads/[^/]+/history")),
    ("GET", re.compile(r"/threads/[^/]+/runs/[^/]+/join")),
)


def is_allowed(method: str, path: str) -> bool:
    normalized_method = method.strip().upper()
    normalized_path = _normalize_path(path)
    for allowed_method, pattern in _ALLOWED_PATTERNS:
        if normalized_method == allowed_method and pattern.fullmatch(normalized_path):
            return True
    return False


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        return ""
    normalized = normalized.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized
