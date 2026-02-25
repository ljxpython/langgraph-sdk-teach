from __future__ import annotations

import contextlib

from langchain.agents import create_agent

from graph_src_v2.config import AppRuntimeConfig
from graph_src_v2.app.memory_policy import apply_persistence_policy
from graph_src_v2.app.models import apply_model_runtime_params, resolve_model
from graph_src_v2.app.persistence import build_checkpointer, build_store
from graph_src_v2.middlewares.registry import build_middleware
from graph_src_v2.tools.registry import build_tools


@contextlib.asynccontextmanager
async def build_runtime_agent(options: AppRuntimeConfig):
    with contextlib.ExitStack() as stack:
        options = apply_persistence_policy(options)
        checkpointer = build_checkpointer(options, stack)
        store = build_store(options, stack)
        tools = await build_tools(options)
        middleware = build_middleware(options)
        model = apply_model_runtime_params(
            resolve_model(options.model_spec),
            options,
        )

        kwargs = {"checkpointer": checkpointer}
        if store is not None:
            kwargs["store"] = store

        runtime_agent = create_agent(
            model=model,
            tools=tools,
            middleware=middleware,
            system_prompt=options.system_prompt,
            **kwargs,
        )
        yield runtime_agent
