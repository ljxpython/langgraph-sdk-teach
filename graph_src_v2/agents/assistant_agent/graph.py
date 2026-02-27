from __future__ import annotations

from typing import Any, cast

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_config
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from graph_src_v2.agents.assistant_agent.prompts import resolve_assistant_system_prompt
from graph_src_v2.agents.assistant_agent.tools import build_assistant_tools, build_langchain_concepts_demo_tools
from graph_src_v2.runtime.modeling import apply_model_runtime_params, resolve_model
from graph_src_v2.runtime.options import (
    build_runtime_config,
    context_to_mapping,
    merge_trusted_auth_context,
)
from graph_src_v2.middlewares.message_sanitizer import MessageSanitizerMiddleware
from graph_src_v2.middlewares.tool_error_guard import ToolErrorGuardMiddleware
from graph_src_v2.runtime.context import RuntimeContext


_ASSISTANT_HITL_CHECKPOINTER = InMemorySaver()


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


def _format_model_credential_error(options: Any, exc: BaseException) -> str:
    model_spec = getattr(options, "model_spec", None)
    provider = getattr(model_spec, "model_provider", None)
    model_name = getattr(model_spec, "model", None)
    base_url = getattr(model_spec, "base_url", None)

    parts: list[str] = ["模型鉴权失败：当前模型调用被拒绝（通常是 API Key 无效/被禁用）。"]
    if provider:
        parts.append(f"provider={provider}")
    if model_name:
        parts.append(f"model={model_name}")
    if base_url:
        parts.append(f"base_url={base_url}")
    if len(parts) > 1:
        header = "（" + ", ".join(parts[1:]) + "）"
    else:
        header = ""

    return (
        parts[0]
        + header
        + "\n\n解决方式：\n"
        + "1) 在 `graph_src_v2/.env` 中配置 `MODEL_ID` 对应模型组所需的 key（见 `conf/settings.yaml`）。\n"
        + "2) 如果你在用 OpenAI-compatible 中转（`OPENAI_BASE_URL`），请确认该中转服务的 key 未被禁用。\n"
        + "3) 需要切模型时仅传 `model_id`，其余连接参数由 settings.yaml 模型组映射。\n\n"
        + f"原始错误：{exc}"
    )


def _format_model_connection_error(options: Any, exc: BaseException) -> str:
    model_spec = getattr(options, "model_spec", None)
    provider = getattr(model_spec, "model_provider", None)
    model_name = getattr(model_spec, "model", None)
    base_url = getattr(model_spec, "base_url", None)

    parts: list[str] = ["模型连接失败：无法连通模型服务（通常是网络/域名/代理/base_url 配置问题）。"]
    if provider:
        parts.append(f"provider={provider}")
    if model_name:
        parts.append(f"model={model_name}")
    if base_url:
        parts.append(f"base_url={base_url}")
    header = "（" + ", ".join(parts[1:]) + "）" if len(parts) > 1 else ""

    return (
        parts[0]
        + header
        + "\n\n排查建议：\n"
        + "1) 确认 `MODEL_ID` 映射到的 `base_url` 可访问（本机 curl 一下）。\n"
        + "2) 如果在公司网络/需要代理，配置 HTTP(S) 代理或切换到可直连的模型服务。\n"
        + "3) 如果你只想本地跑通 UI，可临时切到本地模型（例如 Ollama）或使用可用的中转。\n\n"
        + f"原始错误：{exc}"
    )


async def _run_assistant(
    state: MessagesState,
    *,
    runtime: Runtime[RuntimeContext],
) -> MessagesState:
    config: RunnableConfig = get_config()
    # Trusted auth fields are injected by server/auth middleware and override
    # any same-name fields from client context.
    runtime_context = merge_trusted_auth_context(config, context_to_mapping(runtime.context))
    options = build_runtime_config(config, runtime_context)

    demo_enabled = True

    model = apply_model_runtime_params(
        resolve_model(options.model_spec),
        options,
    )
    tools = await build_assistant_tools(options)
    if demo_enabled:
        tools.extend(build_langchain_concepts_demo_tools(model))

    middleware = cast(
        list[Any],
        [
            MessageSanitizerMiddleware(),
            ToolErrorGuardMiddleware(),
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "request_human_approval": {
                        "allowed_decisions": ["approve", "edit", "reject"],
                    },
                    "send_demo_email": {
                        "allowed_decisions": ["approve", "edit", "reject"],
                    },
                },
                description_prefix="Tool execution pending approval",
            ),
        ],
    )
    system_prompt = resolve_assistant_system_prompt(options.system_prompt, demo_enabled)

    agent_graph = create_agent(
        model=model,
        tools=tools,
        middleware=middleware,
        system_prompt=system_prompt,
        context_schema=RuntimeContext,
        name="assistant",
        checkpointer=_ASSISTANT_HITL_CHECKPOINTER,
    )

    try:
        result = await agent_graph.ainvoke(
            cast(Any, {"messages": state.get("messages", [])}),
            config=config,
            context=runtime.context,
        )
        return {"messages": result.get("messages", [])}
    except Exception as e:
        # 让“鉴权/Key”问题以正常对话消息返回，避免整次 run 失败并刷堆栈。
        if _is_model_credential_error(e):
            return {"messages": [AIMessage(content=_format_model_credential_error(options, e))]}
        # 连接类错误同理（避免 SDK 返回 internal error）。
        if _is_model_connection_error(e):
            return {"messages": [AIMessage(content=_format_model_connection_error(options, e))]}
        raise


_builder = StateGraph(MessagesState, context_schema=RuntimeContext)
_builder.add_node("run_assistant", _run_assistant)
_builder.add_edge(START, "run_assistant")
_builder.add_edge("run_assistant", END)

graph = _builder.compile(name="assistant")



if __name__ == '__main__':
    import asyncio

    from langchain_core.messages import HumanMessage

    async def _main() -> None:
        resp = await graph.ainvoke(
            {"messages": [HumanMessage(content="你好")]},
            config={"recursion_limit": 10},
        )
        print(resp)

    asyncio.run(_main())
