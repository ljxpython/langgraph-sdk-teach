from __future__ import annotations

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from graph_src_v2.agents.router_knowledge_base_agent.tools import (
    build_router_workflow,
    invoke_router_from_messages,
)
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
        "Router knowledge base model authentication failed. "
        "Check MODEL_ID mapping and API key in graph_src_v2/conf/settings.yaml.\n\n"
        f"Raw error: {exc}"
    )


def _format_model_connection_error(exc: BaseException) -> str:
    return (
        "Router knowledge base model connection failed. "
        "Check model base_url and network reachability.\n\n"
        f"Raw error: {exc}"
    )


async def _run_router_knowledge_base(
    state: MessagesState,
    *,
    runtime: Runtime[RuntimeContext],
) -> MessagesState:
    config: RunnableConfig = get_config()
    runtime_context = merge_trusted_auth_context(config, context_to_mapping(runtime.context))
    options = build_runtime_config(config, runtime_context)

    model = apply_model_runtime_params(resolve_model(options.model_spec), options)
    workflow = build_router_workflow(model)

    try:
        routed = invoke_router_from_messages(workflow, list(state.get("messages", [])))
        final_answer = str(routed.get("final_answer") or "No answer generated.")
        return {"messages": [AIMessage(content=final_answer)]}
    except Exception as e:
        if _is_model_credential_error(e):
            return {"messages": [AIMessage(content=_format_model_credential_error(e))]}
        if _is_model_connection_error(e):
            return {"messages": [AIMessage(content=_format_model_connection_error(e))]}
        raise


_builder = StateGraph(MessagesState, context_schema=RuntimeContext)
_builder.add_node("run_router_knowledge_base", _run_router_knowledge_base)
_builder.add_edge(START, "run_router_knowledge_base")
_builder.add_edge("run_router_knowledge_base", END)

graph = _builder.compile(name="router_knowledge_base_demo")
