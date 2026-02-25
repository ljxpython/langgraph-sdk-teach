from __future__ import annotations

import contextlib
import importlib
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from graph_src_v1.config import AppRuntimeConfig


def _enter_context_if_needed(stack: contextlib.ExitStack, value: Any) -> Any:
    if hasattr(value, "__enter__") and hasattr(value, "__exit__"):
        return stack.enter_context(value)
    return value


def _call_setup_if_exists(value: Any) -> None:
    setup = getattr(value, "setup", None)
    if callable(setup):
        setup()


def build_checkpointer(options: AppRuntimeConfig, stack: contextlib.ExitStack) -> Any:
    if options.memory_backend == "memory":
        return InMemorySaver()

    if options.memory_backend != "postgres":
        raise ValueError(f"Unsupported memory backend: {options.memory_backend}")
    if not options.postgres_dsn:
        raise ValueError("POSTGRES_DSN is required when memory_backend=postgres")

    module = importlib.import_module("langgraph.checkpoint.postgres")
    postgres_saver = getattr(module, "PostgresSaver")
    saver_cm = postgres_saver.from_conn_string(options.postgres_dsn)
    saver = stack.enter_context(saver_cm)
    _call_setup_if_exists(saver)
    return saver


def build_store(options: AppRuntimeConfig, stack: contextlib.ExitStack) -> Any | None:
    if options.store_backend == "none":
        return None

    if options.store_backend == "memory":
        try:
            module = importlib.import_module("langgraph.store.memory")
        except ModuleNotFoundError:
            return None
        in_memory_store = getattr(module, "InMemoryStore")
        return in_memory_store()

    if options.store_backend != "redis":
        raise ValueError(f"Unsupported store backend: {options.store_backend}")
    if not options.redis_url:
        raise ValueError("REDIS_URL is required when store_backend=redis")

    try:
        module = importlib.import_module("langgraph.store.redis")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Redis store backend requires langgraph Redis store package. "
            "Install compatible Redis store dependencies first."
        ) from exc

    redis_store_cls = getattr(module, "RedisStore")
    if hasattr(redis_store_cls, "from_conn_string"):
        candidate = redis_store_cls.from_conn_string(options.redis_url)
    else:
        candidate = redis_store_cls(url=options.redis_url)

    store = _enter_context_if_needed(stack, candidate)
    _call_setup_if_exists(store)
    return store
