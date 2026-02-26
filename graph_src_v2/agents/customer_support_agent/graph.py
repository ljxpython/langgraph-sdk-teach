from __future__ import annotations

from typing import Any, cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from graph_src_v2.agents.customer_support_agent.tools import SupportState, build_customer_support_agent
from graph_src_v2.runtime.context import RuntimeContext
from graph_src_v2.runtime.modeling import apply_model_runtime_params, resolve_model
from graph_src_v2.runtime.options import build_runtime_config, context_to_mapping, merge_trusted_auth_context


def _is_model_credential_error(exc: BaseException) -> bool:
    name = exc.__class__.__name__
    if name in {"AuthenticationError", "PermissionDeniedError"}:
        return True
    text = str(exc)
    needles = [
        "Invalid API key",
        "API key is disabled",
        "Incorrect API key",
        "Missing API key",
        "401",
        "Unauthorized",
    ]
    return any(n in text for n in needles)


def _is_model_connection_error(exc: BaseException) -> bool:
    name = exc.__class__.__name__
    if name in {"APIConnectionError", "APITimeoutError", "TimeoutError"}:
        return True
    text = str(exc)
    needles = [
        "Connection error",
        "All connection attempts failed",
        "ConnectTimeout",
        "ReadTimeout",
        "timed out",
        "Name or service not known",
        "Temporary failure in name resolution",
    ]
    return any(n in text for n in needles)


def _format_model_credential_error(exc: BaseException) -> str:
    return (
        "Customer support model authentication failed. "
        "Check MODEL_ID mapping and API key in graph_src_v2/conf/settings.yaml.\n\n"
        f"Raw error: {exc}"
    )


def _format_model_connection_error(exc: BaseException) -> str:
    return (
        "Customer support model connection failed. "
        "Check model base_url and network reachability.\n\n"
        f"Raw error: {exc}"
    )


async def _run_customer_support(
    state: SupportState,
    *,
    runtime: Runtime[RuntimeContext],
) -> SupportState:
    config: RunnableConfig = get_config()
    runtime_context = merge_trusted_auth_context(config, context_to_mapping(runtime.context))
    options = build_runtime_config(config, runtime_context)

    model = apply_model_runtime_params(resolve_model(options.model_spec), options)
    agent = build_customer_support_agent(model)

    try:
        result = await agent.ainvoke(cast(dict[str, Any], state), config=config, context=runtime.context)
        return cast(SupportState, result)
    except Exception as e:
        if _is_model_credential_error(e):
            return cast(SupportState, {"messages": [AIMessage(content=_format_model_credential_error(e))]})
        if _is_model_connection_error(e):
            return cast(SupportState, {"messages": [AIMessage(content=_format_model_connection_error(e))]})
        raise


_builder = StateGraph(SupportState, context_schema=RuntimeContext)
_builder.add_node("run_customer_support", _run_customer_support)
_builder.add_edge(START, "run_customer_support")
_builder.add_edge("run_customer_support", END)

graph = _builder.compile(name="customer_support_handoffs_demo")
