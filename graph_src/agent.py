from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import importlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph_sdk.runtime import ServerRuntime

from graph_src.llms import get_kimi_model, get_mass_deepseek_model, get_mass_glm_4_model

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert researcher. Your job is to conduct thorough research and then "
    "write a polished report."
)


@dataclass
class RuntimeOptions:
    model_provider: str = "glm4"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    enable_local_tools: bool = True
    enable_local_mcp: bool = False
    mcp_servers: list[str] | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None


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


def _read_configurable(config: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(config, Mapping):
        return {}
    configurable = config.get("configurable")
    return configurable if isinstance(configurable, Mapping) else {}


def _context_to_mapping(raw: Any) -> Mapping[str, Any]:
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
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    values = [str(item).strip() for item in parsed if str(item).strip()]
                else:
                    values = [text]
            except json.JSONDecodeError:
                values = _split_csv(text)
        else:
            values = _split_csv(text)
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


def build_runtime_options(
    config: Mapping[str, Any] | None,
    runtime_context: Mapping[str, Any] | None = None,
) -> RuntimeOptions:
    configurable = _read_configurable(config)
    context_data = runtime_context or {}

    model_provider = str(
        context_data.get("model_provider")
        or context_data.get("llm_provider")
        or configurable.get("model_provider")
        or configurable.get("x-model-provider")
        or "glm4"
    )
    system_prompt = str(
        context_data.get("system_prompt")
        or context_data.get("system_message")
        or configurable.get("system_prompt")
        or configurable.get("x-system-prompt")
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
    if raw_servers is None:
        raw_servers = context_data.get("mcp_server")
    if raw_servers is None:
        raw_servers = (
            configurable.get("mcp_server")
            if "mcp_server" in configurable
            else configurable.get("x-mcp-server")
        )
    mcp_servers = _parse_mcp_servers(raw_servers)
    if not enable_local_mcp:
        mcp_servers = []
    if enable_local_mcp and not mcp_servers:
        mcp_servers = ["local_math"]

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

    return RuntimeOptions(
        model_provider=model_provider,
        system_prompt=system_prompt,
        enable_local_tools=enable_local_tools,
        enable_local_mcp=enable_local_mcp,
        mcp_servers=mcp_servers,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
    )


def resolve_model(model_provider: str):
    provider = model_provider.strip().lower()
    if provider in {"deepseek", "mass_deepseek"}:
        return get_mass_deepseek_model()
    if provider in {"kimi", "mass_kimi"}:
        return get_kimi_model()
    return get_mass_glm_4_model()


def apply_model_runtime_params(model: Any, options: RuntimeOptions) -> Any:
    kwargs: dict[str, Any] = {}
    if options.temperature is not None:
        kwargs["temperature"] = options.temperature
    if options.max_tokens is not None:
        kwargs["max_tokens"] = options.max_tokens
    if options.top_p is not None:
        kwargs["top_p"] = options.top_p
    if not kwargs:
        return model
    return model.bind(**kwargs)


@tool
def word_count(text: str) -> int:
    """Count words in a text string."""

    return len([w for w in text.split() if w.strip()])


@tool
def utc_now() -> str:
    """Return current UTC time in ISO 8601 format."""

    return datetime.now(timezone.utc).isoformat()


@tool
def to_upper(text: str) -> str:
    """Convert text to uppercase."""

    return text.upper()


def get_local_tools() -> list[Any]:
    return [word_count, utc_now, to_upper]


def get_mcp_server_specs() -> dict[str, dict[str, Any]]:
    math_server = Path(__file__).with_name("local_mcp_server.py").resolve()
    text_server = Path(__file__).with_name("local_text_mcp_server.py").resolve()
    return {
        "local_math": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(math_server)],
        },
        "local_text": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(text_server)],
        },
    }


async def get_mcp_tools(server_names: list[str]) -> list[Any]:
    if not server_names:
        return []

    mcp_client_module = await asyncio.to_thread(
        importlib.import_module,
        "langchain_mcp_adapters.client",
    )
    MultiServerMCPClient = getattr(mcp_client_module, "MultiServerMCPClient")

    specs = get_mcp_server_specs()
    selected: dict[str, dict[str, Any]] = {}
    for name in server_names:
        if name not in specs:
            allowed = ", ".join(sorted(specs.keys()))
            raise ValueError(f"Unsupported mcp server '{name}', allowed: {allowed}")
        selected[name] = specs[name]

    client = MultiServerMCPClient(selected)
    return await client.get_tools()


async def build_agent_from_config(
    config: Mapping[str, Any] | None,
    runtime_context: Mapping[str, Any] | None = None,
):
    options = build_runtime_options(config, runtime_context)
    tools: list[Any] = []

    if options.enable_local_tools:
        tools.extend(get_local_tools())
    if options.enable_local_mcp:
        tools.extend(await get_mcp_tools(options.mcp_servers or []))

    runtime_model = apply_model_runtime_params(resolve_model(options.model_provider), options)
    return create_agent(
        model=runtime_model,
        tools=tools,
        system_prompt=options.system_prompt,
    )


@contextlib.asynccontextmanager
async def make_graph(config: RunnableConfig, runtime: ServerRuntime):
    run_context: Mapping[str, Any] = {}
    execution_runtime = runtime.execution_runtime
    if execution_runtime is not None:
        run_context = _context_to_mapping(execution_runtime.context)

    runtime_agent = await build_agent_from_config(config, run_context)
    yield runtime_agent


agent_not_deep = create_agent(
    model=resolve_model("glm4"),
    tools=get_local_tools(),
    system_prompt=DEFAULT_SYSTEM_PROMPT,
)


@contextlib.asynccontextmanager
async def agent(config: RunnableConfig, runtime: ServerRuntime):
    async with make_graph(config, runtime) as runtime_agent:
        yield runtime_agent
