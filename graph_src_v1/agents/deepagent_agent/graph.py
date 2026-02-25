from __future__ import annotations

import contextlib
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.subagents import CompiledSubAgent, SubAgent
from langchain_core.runnables import RunnableConfig
from langchain.agents.middleware.human_in_the_loop import InterruptOnConfig
from langgraph_sdk.runtime import ServerRuntime

from graph_src_v1.app.models import apply_model_runtime_params, resolve_model
from graph_src_v1.config import DEFAULT_SYSTEM_PROMPT, build_runtime_config, context_to_mapping, read_configurable
from graph_src_v1.agents.deepagent_agent.prompts import SYSTEM_PROMPT
from graph_src_v1.agents.deepagent_agent.tools import list_deepagent_skills, list_subagents
from graph_src_v1.agents.deepagent_agent.state import DeepAgentContext
from graph_src_v1.tools.registry import build_tools

ROOT_DIR = Path(__file__).resolve().parents[2]


def _interrupt_on() -> dict[str, bool | InterruptOnConfig]:
    return {
        "write_todos": True,
        "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "edit_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        "task": {"allowed_decisions": ["approve", "reject"]},
    }

def _parse_string_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        values = [str(raw).strip()]
    return [item for item in values if item]


def _parse_subagents(raw: Any) -> list[SubAgent]:
    if not isinstance(raw, list):
        return []
    parsed: list[SubAgent] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        description = item.get("description")
        if not isinstance(description, str):
            continue
        system_prompt = item.get("system_prompt")
        if not isinstance(system_prompt, str):
            continue
        skills = _parse_string_list(item.get("skills"))
        parsed.append(
            SubAgent(
                name=name.strip(),
                description=description,
                system_prompt=system_prompt,
                skills=skills,
            )
        )
    return parsed


def _pick_dynamic_value(
    context_data: Mapping[str, Any], configurable: Mapping[str, Any], *keys: str
) -> Any:
    for key in keys:
        if key in context_data:
            return context_data.get(key)
    for key in keys:
        if key in configurable:
            return configurable.get(key)
    return None


def _resolve_system_prompt(
    context_data: Mapping[str, Any], configurable: Mapping[str, Any], fallback: str
) -> str:
    raw = _pick_dynamic_value(context_data, configurable, "system_prompt", "system_message", "x-system-prompt")
    if raw is None:
        return SYSTEM_PROMPT if fallback == DEFAULT_SYSTEM_PROMPT else fallback
    text = str(raw).strip()
    return text or SYSTEM_PROMPT


def _resolve_skills(context_data: Mapping[str, Any], configurable: Mapping[str, Any]) -> list[str]:
    raw = _pick_dynamic_value(context_data, configurable, "skills", "deepagent_skills", "x-deepagent-skills")
    parsed = _parse_string_list(raw)
    return parsed if parsed else list_deepagent_skills()


def _resolve_subagents(
    context_data: Mapping[str, Any], configurable: Mapping[str, Any]
) -> list[SubAgent | CompiledSubAgent]:
    raw = _pick_dynamic_value(
        context_data,
        configurable,
        "subagents",
        "deepagent_subagents",
        "x-deepagent-subagents",
    )
    parsed = _parse_subagents(raw)
    resolved: list[SubAgent | CompiledSubAgent] = []
    if parsed:
        resolved.extend(parsed)
        return resolved
    resolved.extend(list_subagents())
    return resolved


@contextlib.asynccontextmanager
async def make_graph(config: RunnableConfig, runtime: ServerRuntime[DeepAgentContext]):
    run_context: Mapping[str, Any] = {}
    execution_runtime = runtime.execution_runtime
    if execution_runtime is not None:
        run_context = context_to_mapping(execution_runtime.context)

    configurable = read_configurable(config)
    options = build_runtime_config(config, run_context)
    tools = await build_tools(options)
    model = apply_model_runtime_params(
        resolve_model(
            options.model_provider,
            model_name=options.model_name,
            base_url=options.model_base_url,
            api_key=options.model_api_key,
        ),
        options,
    )

    deep_agent = create_deep_agent(
        name="deepagent-demo",
        model=model,
        tools=tools,
        system_prompt=_resolve_system_prompt(run_context, configurable, options.system_prompt),
        backend=FilesystemBackend(root_dir=str(ROOT_DIR), virtual_mode=False),
        skills=_resolve_skills(run_context, configurable),
        subagents=_resolve_subagents(run_context, configurable),
        interrupt_on=_interrupt_on(),
        context_schema=DeepAgentContext,
    )
    yield deep_agent


@contextlib.asynccontextmanager
async def deepagent_demo(config: RunnableConfig, runtime: ServerRuntime[DeepAgentContext]):
    async with make_graph(config, runtime) as runtime_agent:
        yield runtime_agent
