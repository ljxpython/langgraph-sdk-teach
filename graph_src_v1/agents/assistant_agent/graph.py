from __future__ import annotations

import contextlib
from typing import Any, Mapping

from langchain_core.runnables import RunnableConfig
from langgraph_sdk.runtime import ServerRuntime

from graph_src_v1.agents.assistant_agent.state import AssistantAgentContext
from graph_src_v1.config import build_runtime_config, context_to_mapping
from graph_src_v1.app.factory import build_runtime_agent


@contextlib.asynccontextmanager
async def make_graph(config: RunnableConfig, runtime: ServerRuntime[AssistantAgentContext]):
    run_context: Mapping[str, Any] = {}
    execution_runtime = runtime.execution_runtime
    if execution_runtime is not None:
        run_context = context_to_mapping(execution_runtime.context)

    runtime_options = build_runtime_config(config, run_context)
    async with build_runtime_agent(runtime_options) as runtime_agent:
        yield runtime_agent


@contextlib.asynccontextmanager
async def agent(config: RunnableConfig, runtime: ServerRuntime[AssistantAgentContext]):
    async with make_graph(config, runtime) as runtime_agent:
        yield runtime_agent
