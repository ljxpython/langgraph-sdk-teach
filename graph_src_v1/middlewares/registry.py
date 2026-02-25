from __future__ import annotations

from typing import Callable

from langchain.agents.middleware import AgentMiddleware

from graph_src_v1.config import AppRuntimeConfig
from graph_src_v1.middlewares.message_sanitizer import MessageSanitizerMiddleware
from graph_src_v1.middlewares.tool_error_guard import ToolErrorGuardMiddleware

MiddlewareFactory = Callable[[], AgentMiddleware]

MIDDLEWARE_REGISTRY: dict[str, MiddlewareFactory] = {
    "message_sanitizer": MessageSanitizerMiddleware,
    "tool_error_guard": ToolErrorGuardMiddleware,
}

DEFAULT_MIDDLEWARES: list[str] = ["message_sanitizer", "tool_error_guard"]


def _resolve_middleware_names(options: AppRuntimeConfig) -> list[str]:
    # None 表示“未配置 middlewares”，走默认值；空列表 [] 表示“显式禁用”。
    names = DEFAULT_MIDDLEWARES if options.middlewares is None else options.middlewares
    normalized: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = str(name).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def build_middleware(options: AppRuntimeConfig) -> list[AgentMiddleware]:
    middleware: list[AgentMiddleware] = []
    for name in _resolve_middleware_names(options):
        factory = MIDDLEWARE_REGISTRY.get(name)
        if factory is None:
            allowed = ", ".join(sorted(MIDDLEWARE_REGISTRY.keys()))
            raise ValueError(f"Unsupported middleware '{name}', allowed: {allowed}")
        middleware.append(factory())
    return middleware
