from __future__ import annotations

import contextlib

from langchain.agents import create_agent

from graph_src_v1.config import AppRuntimeConfig
from graph_src_v1.app.memory_policy import apply_persistence_policy
from graph_src_v1.app.models import apply_model_runtime_params, resolve_model
from graph_src_v1.app.persistence import build_checkpointer, build_store
from graph_src_v1.middlewares.registry import build_middleware
from graph_src_v1.tools.registry import build_tools


@contextlib.asynccontextmanager
async def build_runtime_agent(options: AppRuntimeConfig):
    with contextlib.ExitStack() as stack:
        options = apply_persistence_policy(options)
        checkpointer = build_checkpointer(options, stack)
        store = build_store(options, stack)
        tools = await build_tools(options)
        middleware = build_middleware(options)
        model = apply_model_runtime_params(
            resolve_model(
                options.model_provider,
                model_name=options.model_name,
                base_url=options.model_base_url,
                api_key=options.model_api_key,
            ),
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
