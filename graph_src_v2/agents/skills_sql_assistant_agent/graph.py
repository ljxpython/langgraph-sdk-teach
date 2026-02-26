from __future__ import annotations

from typing import Any, cast

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from graph_src_v2.agents.skills_sql_assistant_agent.tools import build_skills_sql_assistant_agent
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
        "Skills SQL assistant model authentication failed. "
        "Check MODEL_ID mapping and API key in graph_src_v2/conf/settings.yaml.\n\n"
        f"Raw error: {exc}"
    )


def _format_model_connection_error(exc: BaseException) -> str:
    return (
        "Skills SQL assistant model connection failed. "
        "Check model base_url and network reachability.\n\n"
        f"Raw error: {exc}"
    )


async def _run_skills_sql_assistant(
    state: MessagesState,
    *,
    runtime: Runtime[RuntimeContext],
) -> MessagesState:
    config: RunnableConfig = get_config()
    runtime_context = merge_trusted_auth_context(config, context_to_mapping(runtime.context))
    options = build_runtime_config(config, runtime_context)

    model = apply_model_runtime_params(resolve_model(options.model_spec), options)
    agent = build_skills_sql_assistant_agent(model)

    try:
        result = await agent.ainvoke(
            cast(dict[str, Any], {"messages": state.get("messages", [])}),
            config=config,
            context=runtime.context,
        )
        return {"messages": result.get("messages", [])}
    except Exception as e:
        if _is_model_credential_error(e):
            return {"messages": [AIMessage(content=_format_model_credential_error(e))]}
        if _is_model_connection_error(e):
            return {"messages": [AIMessage(content=_format_model_connection_error(e))]}
        raise


_builder = StateGraph(MessagesState, context_schema=RuntimeContext)
_builder.add_node("run_skills_sql_assistant", _run_skills_sql_assistant)
_builder.add_edge(START, "run_skills_sql_assistant")
_builder.add_edge("run_skills_sql_assistant", END)

graph = _builder.compile(name="skills_sql_assistant_demo")
