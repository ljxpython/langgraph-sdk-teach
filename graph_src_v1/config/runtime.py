from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from typing import Any, Mapping

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert researcher. Your job is to conduct thorough research and then "
    "write a polished report."
)


@dataclass
class AppRuntimeConfig:
    environment: str = "dev"
    model_provider: str = "glm4"
    model_name: str | None = None
    model_base_url: str | None = None
    model_api_key: str | None = None
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    enable_local_tools: bool = True
    enable_local_mcp: bool = False
    mcp_servers: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    middlewares: list[str] | None = None
    persistence_profile: str | None = None
    memory_backend: str = "memory"
    store_backend: str = "memory"
    postgres_dsn: str | None = None
    redis_url: str | None = None


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _parse_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_configurable(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(config, Mapping):
        return {}
    configurable = config.get("configurable")
    return configurable if isinstance(configurable, Mapping) else {}


def context_to_mapping(raw: Any) -> Mapping[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, Mapping):
        return raw
    if dataclasses.is_dataclass(raw) and not isinstance(raw, type):
        return dataclasses.asdict(raw)
    if hasattr(raw, "__dict__") and isinstance(raw.__dict__, dict):
        return raw.__dict__
    return {}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_mcp_servers(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        values = _split_csv(raw)
    else:
        values = [str(raw).strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = item.lower()
        if key in {"", "none"} or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _parse_middleware_names(raw: Any) -> list[str] | None:
    # None 表示“未配置 middlewares”，由中间件层选择默认值。
    # 显式传 "none" / [] / 空字符串等，解析结果会是 []，表示“禁用中间件”。
    if raw is None:
        return None
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        values = _split_csv(raw)
    else:
        values = [str(raw).strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = item.lower()
        if key in {"", "none"} or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def build_runtime_config(
    config: Mapping[str, Any] | None,
    runtime_context: Mapping[str, Any] | None = None,
) -> AppRuntimeConfig:
    configurable = read_configurable(config)
    context_data = runtime_context or {}

    environment = str(
        context_data.get("environment")
        or configurable.get("environment")
        or os.getenv("APP_ENV")
        or "dev"
    ).lower()

    default_memory_backend = "postgres" if environment in {"prod", "production"} else "memory"
    default_store_backend = "redis" if environment in {"prod", "production"} else "memory"

    memory_backend = str(
        context_data.get("memory_backend")
        or configurable.get("memory_backend")
        or os.getenv("MEMORY_BACKEND")
        or default_memory_backend
    ).lower()
    store_backend = str(
        context_data.get("store_backend")
        or configurable.get("store_backend")
        or os.getenv("STORE_BACKEND")
        or default_store_backend
    ).lower()
    persistence_profile_raw = (
        context_data.get("persistence_profile")
        or configurable.get("persistence_profile")
        or configurable.get("x-persistence-profile")
        or os.getenv("PERSISTENCE_PROFILE")
    )
    persistence_profile = (
        str(persistence_profile_raw).strip().lower() if persistence_profile_raw is not None else None
    ) or None

    model_provider = str(
        context_data.get("model_provider")
        or context_data.get("llm_provider")
        or configurable.get("model_provider")
        or configurable.get("x-model-provider")
        or os.getenv("MODEL_PROVIDER")
        or "glm4"
    )
    model_name = (
        context_data.get("model_name")
        or context_data.get("model")
        or configurable.get("model_name")
        or configurable.get("model")
        or configurable.get("x-model")
        or os.getenv("MODEL_NAME")
    )
    model_name = str(model_name).strip() if model_name is not None else None
    model_name = model_name or None

    model_base_url = (
        context_data.get("model_base_url")
        or context_data.get("base_url")
        or configurable.get("model_base_url")
        or configurable.get("base_url")
        or configurable.get("x-model-base-url")
        or os.getenv("MODEL_BASE_URL")
    )
    model_base_url = str(model_base_url).strip() if model_base_url is not None else None
    model_base_url = model_base_url or None

    model_api_key = (
        context_data.get("model_api_key")
        or configurable.get("model_api_key")
        or configurable.get("x-model-api-key")
        or os.getenv("MODEL_API_KEY")
    )
    model_api_key = str(model_api_key).strip() if model_api_key is not None else None
    model_api_key = model_api_key or None

    system_prompt = str(
        context_data.get("system_prompt")
        or context_data.get("system_message")
        or configurable.get("system_prompt")
        or configurable.get("x-system-prompt")
        or os.getenv("SYSTEM_PROMPT")
        or DEFAULT_SYSTEM_PROMPT
    )
    enable_local_tools = _parse_bool(
        context_data.get("enable_local_tools")
        if "enable_local_tools" in context_data
        else (
            configurable.get("enable_local_tools")
            if "enable_local_tools" in configurable
            else configurable.get("x-enable-local-tools")
        ),
        default=True,
    )
    enable_local_mcp = _parse_bool(
        context_data.get("enable_local_mcp")
        if "enable_local_mcp" in context_data
        else (
            configurable.get("enable_local_mcp")
            if "enable_local_mcp" in configurable
            else configurable.get("x-enable-local-mcp")
        ),
        default=False,
    )

    raw_servers = context_data.get("mcp_servers")
    if raw_servers is None:
        raw_servers = (
            configurable.get("mcp_servers")
            if "mcp_servers" in configurable
            else configurable.get("x-mcp-servers")
        )
    mcp_servers = _parse_mcp_servers(raw_servers)
    if not enable_local_mcp:
        mcp_servers = []
    if enable_local_mcp and not mcp_servers:
        mcp_servers = ["local_math"]

    raw_middlewares = context_data.get("middlewares")
    if raw_middlewares is None:
        raw_middlewares = (
            configurable.get("middlewares")
            if "middlewares" in configurable
            else configurable.get("x-middlewares")
        )
    if raw_middlewares is None:
        raw_middlewares = os.getenv("MIDDLEWARES")
    middlewares = _parse_middleware_names(raw_middlewares)

    temperature = _parse_float(
        context_data.get("temperature")
        if "temperature" in context_data
        else configurable.get("temperature"),
        default=None,
    )
    top_p = _parse_float(
        context_data.get("top_p") if "top_p" in context_data else configurable.get("top_p"),
        default=None,
    )
    max_tokens = _parse_int(
        context_data.get("max_tokens")
        if "max_tokens" in context_data
        else configurable.get("max_tokens"),
        default=None,
    )

    postgres_dsn = str(
        context_data.get("postgres_dsn")
        or configurable.get("postgres_dsn")
        or os.getenv("POSTGRES_DSN")
        or ""
    ).strip() or None
    redis_url = str(
        context_data.get("redis_url")
        or configurable.get("redis_url")
        or os.getenv("REDIS_URL")
        or ""
    ).strip() or None

    return AppRuntimeConfig(
        environment=environment,
        model_provider=model_provider,
        model_name=model_name,
        model_base_url=model_base_url,
        model_api_key=model_api_key,
        system_prompt=system_prompt,
        enable_local_tools=enable_local_tools,
        enable_local_mcp=enable_local_mcp,
        mcp_servers=mcp_servers,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        middlewares=middlewares,
        persistence_profile=persistence_profile,
        memory_backend=memory_backend,
        store_backend=store_backend,
        postgres_dsn=postgres_dsn,
        redis_url=redis_url,
    )
