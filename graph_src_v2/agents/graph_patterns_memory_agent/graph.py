from __future__ import annotations

import re
from typing import Any, cast
from uuid import uuid4

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from graph_src_v2.agents.graph_patterns_memory_agent.prompts import ROOT_SYSTEM_PROMPT
from graph_src_v2.agents.graph_patterns_memory_agent.tools import (
    build_multi_agent_tools,
    extract_memory_candidate,
    send_demo_email,
)
from graph_src_v2.runtime.context import RuntimeContext
from graph_src_v2.runtime.modeling import apply_model_runtime_params, resolve_model
from graph_src_v2.runtime.options import build_runtime_config, context_to_mapping, merge_trusted_auth_context


class DemoState(MessagesState):
    approval_rejected: bool
    skip_specialists: bool
    approved_email_action: dict[str, Any] | None


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
        "Graph patterns memory demo model authentication failed. "
        "Check MODEL_ID mapping and API key in graph_src_v2/conf/settings.yaml.\n\n"
        f"Raw error: {exc}"
    )


def _format_model_connection_error(exc: BaseException) -> str:
    return (
        "Graph patterns memory demo model connection failed. "
        "Check model base_url and network reachability.\n\n"
        f"Raw error: {exc}"
    )


def _last_human_message_text(state: MessagesState) -> str:
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text)
            joined = "\n".join(parts).strip()
            if joined:
                return joined
        return str(content)

    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return _content_to_text(message.content)
        if isinstance(message, dict) and message.get("type") == "human":
            return _content_to_text(message.get("content", ""))
        if getattr(message, "type", None) == "human":
            return _content_to_text(getattr(message, "content", ""))
    return ""


def _requires_human_review(text: str) -> bool:
    if extract_memory_candidate(text) is not None:
        return False

    lowered = text.lower()
    keywords = [
        "request_human_approval",
        "人工审批",
        "人工评审",
        "审批",
        "send_demo_email",
        "发送邮件",
        "发邮件",
        "邮件通知",
        "email",
    ]
    return any(keyword in lowered for keyword in keywords)


def _is_email_intent(text: str) -> bool:
    lowered = text.lower()
    email_keywords = ["发送邮件", "发邮件", "邮件", "email"]
    return any(k in lowered for k in email_keywords)


def _extract_recent_email_recipients(state: MessagesState) -> list[str]:
    for message in reversed(state.get("messages", [])):
        if getattr(message, "type", None) != "tool":
            continue
        if getattr(message, "name", None) != "send_demo_email":
            continue
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            continue
        match = re.search(r"Email sent to\s+(.+?)\.\s+Subject:", content)
        if not match:
            continue
        recipients_raw = match.group(1)
        recipients = [part.strip() for part in recipients_raw.split(",") if part.strip()]
        if recipients:
            return recipients
    return []


def _extract_email_action(text: str, state: MessagesState) -> dict[str, Any] | None:
    if not _is_email_intent(text):
        return None

    found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    recipients = list(dict.fromkeys(found))
    if not recipients and any(
        token in text.lower()
        for token in ["再次", "再发", "再来一封", "同一个", "那个", "他", "她", "ta", "him", "her", "same"]
    ):
        recipients = _extract_recent_email_recipients(state)
    if not recipients:
        return None

    return {
        "name": "send_demo_email",
        "args": {
            "to": recipients,
            "subject": "上线通知",
            "body": text,
        },
        "arguments": {
            "to": recipients,
            "subject": "上线通知",
            "body": text,
        },
        "description": (
            "Tool execution pending approval\n\n"
            "Tool: send_demo_email\n"
            f"To: {recipients}\n"
            "Subject: 上线通知"
        ),
    }


def _extract_edited_action(resume_payload: Any) -> dict[str, Any] | None:
    if not isinstance(resume_payload, dict):
        return None
    decisions = resume_payload.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        return None
    first = decisions[0] if isinstance(decisions[0], dict) else {}
    edited_action = first.get("edited_action")
    if not isinstance(edited_action, dict):
        return None
    name = edited_action.get("name")
    args = edited_action.get("args")
    if not isinstance(name, str) or not isinstance(args, dict):
        return None
    return {"name": name, "args": args}


def _extract_review_decision(resume_payload: Any) -> str | None:
    allowed = {"approve", "edit", "reject"}

    if isinstance(resume_payload, dict):
        decisions = resume_payload.get("decisions")
        if isinstance(decisions, list) and decisions:
            first = decisions[0] if isinstance(decisions[0], dict) else {}
            decision_type = first.get("type")
            if isinstance(decision_type, str):
                normalized = decision_type.lower().strip()
                return normalized if normalized in allowed else None
        decision_type = resume_payload.get("type")
        if isinstance(decision_type, str):
            normalized = decision_type.lower().strip()
            return normalized if normalized in allowed else None
    if isinstance(resume_payload, str):
        normalized = resume_payload.lower().strip()
        return normalized if normalized in allowed else None
    return None


async def _load_long_term_memory(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    if runtime.store is None:
        return {"messages": []}

    user_id = runtime.context.user_id or "anonymous"
    namespace = (user_id, "graph_patterns_memories")
    query = _last_human_message_text(state) or "user preferences"
    memories = await runtime.store.asearch(namespace, query=query, limit=3)
    if not memories:
        return {"messages": []}

    lines: list[str] = []
    for item in memories:
        value = item.value if isinstance(item.value, dict) else {}
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            lines.append(f"- {text}")
    if not lines:
        return {"messages": []}

    return {
        "messages": [
            SystemMessage(content="Known long-term memories about this user:\n" + "\n".join(lines))
        ]
    }


async def _run_specialist_subgraph(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    config: RunnableConfig = get_config()
    runtime_context = merge_trusted_auth_context(config, context_to_mapping(runtime.context))
    options = build_runtime_config(config, runtime_context)

    model = apply_model_runtime_params(resolve_model(options.model_spec), options)
    tools = build_multi_agent_tools(model)
    supervisor = create_agent(
        model=model,
        tools=tools,
        system_prompt=options.system_prompt or ROOT_SYSTEM_PROMPT,
        context_schema=RuntimeContext,
        name="graph_patterns_memory_supervisor",
    )

    result = await supervisor.ainvoke(
        cast(Any, {"messages": state.get("messages", [])}),
        config=config,
        context=runtime.context,
    )

    return {"messages": result.get("messages", [])}


async def _human_review_gate(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    del runtime
    request_text = _last_human_message_text(state)
    memory_only_request = extract_memory_candidate(request_text) is not None

    if memory_only_request:
        return {
            "messages": [],
            "approval_rejected": False,
            "skip_specialists": True,
            "approved_email_action": None,
        }

    email_action = _extract_email_action(request_text, state)
    if _is_email_intent(request_text) and email_action is None:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "我已识别到你要发送邮件。为了进入审批并执行发送，请补充收件人邮箱。"
                        "例如：给 ops@example.com 发邮件通知今晚灰度发布。"
                    )
                )
            ],
            "approval_rejected": False,
            "skip_specialists": True,
            "approved_email_action": None,
        }

    if email_action is not None:
        email_review_request = {
            "action_requests": [email_action],
            "review_configs": [
                {
                    "action_name": "send_demo_email",
                    "allowed_decisions": ["approve", "edit", "reject"],
                }
            ],
        }
        resume_payload = interrupt(email_review_request)
        decision = _extract_review_decision(resume_payload)
        if decision is None:
            return {
                "messages": [
                    AIMessage(
                        content=(
                            "未收到有效审批决策，邮件尚未发送。"
                            "请在审批卡片中选择 approve / edit / reject。"
                        )
                    )
                ],
                "approval_rejected": False,
                "skip_specialists": True,
                "approved_email_action": None,
            }
        if decision == "reject":
            return {
                "messages": [
                    AIMessage(content="Human review rejected the email action. Workflow stopped before sending.")
                ],
                "approval_rejected": True,
                "skip_specialists": True,
                "approved_email_action": None,
            }

        edited_action = _extract_edited_action(resume_payload)
        if decision == "edit":
            if edited_action is None or edited_action.get("name") != "send_demo_email":
                return {
                    "messages": [
                        AIMessage(
                            content=(
                                "检测到 edit 决策，但缺少合法 edited_action，邮件未发送。"
                                "请重新提交审批。"
                            )
                        )
                    ],
                    "approval_rejected": False,
                    "skip_specialists": True,
                    "approved_email_action": None,
                }
            approved_action = edited_action
        else:
            approved_action = {"name": "send_demo_email", "args": email_action["args"]}
        decision_note = "Human review approved email action." if decision == "approve" else f"Human review decision: {decision}."
        return {
            "messages": [AIMessage(content=decision_note)],
            "approval_rejected": False,
            "skip_specialists": True,
            "approved_email_action": approved_action,
        }

    if not _requires_human_review(request_text):
        return {
            "messages": [],
            "approval_rejected": False,
            "skip_specialists": False,
            "approved_email_action": None,
        }

    review_request = {
        "action_requests": [
            {
                "name": "request_human_approval",
                "args": {"request": request_text},
                "arguments": {"request": request_text},
                "description": (
                    "Tool execution pending approval\n\n"
                    "Tool: request_human_approval\n"
                    f"Arguments: {{\"request\": {request_text!r}}}"
                ),
            }
        ],
        "review_configs": [
            {
                "action_name": "request_human_approval",
                "allowed_decisions": ["approve", "edit", "reject"],
            }
        ],
    }
    resume_payload = interrupt(review_request)
    decision = _extract_review_decision(resume_payload)
    if decision is None:
        return {
            "messages": [
                AIMessage(content="未收到有效审批决策。请在审批卡片中选择 approve / edit / reject。")
            ],
            "approval_rejected": False,
            "skip_specialists": True,
            "approved_email_action": None,
        }
    if decision == "reject":
        return {
            "messages": [AIMessage(content="Human review rejected this action. Workflow stopped before execution.")],
            "approval_rejected": True,
            "skip_specialists": True,
            "approved_email_action": None,
        }

    decision_note = "Human review approved." if decision == "approve" else f"Human review decision: {decision}."
    return {
        "messages": [AIMessage(content=decision_note)],
        "approval_rejected": False,
        "skip_specialists": False,
        "approved_email_action": None,
    }


async def _execute_approved_email_action(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    del runtime
    action = state.get("approved_email_action")
    if not isinstance(action, dict):
        return {"messages": []}
    action_name = action.get("name")
    if action_name != "send_demo_email":
        return {"messages": []}
    raw_args = action.get("args")
    args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
    to = args.get("to") if isinstance(args.get("to"), list) else []
    subject = str(args.get("subject") or "")
    body = str(args.get("body") or "")
    result = send_demo_email.invoke({"to": to, "subject": subject, "body": body})
    return {"messages": [AIMessage(content=result)]}


async def _persist_long_term_memory(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    if runtime.store is None:
        return {"messages": []}

    last_human = _last_human_message_text(state)
    candidate = extract_memory_candidate(last_human)
    if not candidate:
        return {"messages": []}

    user_id = runtime.context.user_id or "anonymous"
    namespace = (user_id, "graph_patterns_memories")
    await runtime.store.aput(namespace, str(uuid4()), {"text": candidate})
    return {"messages": [AIMessage(content=f"Long-term memory stored: {candidate}")]} 


_subgraph_builder = StateGraph(MessagesState, context_schema=RuntimeContext)
_subgraph_builder.add_node("run_specialist_supervisor", _run_specialist_subgraph)
_subgraph_builder.add_edge(START, "run_specialist_supervisor")
_subgraph_builder.add_edge("run_specialist_supervisor", END)
specialist_subgraph = _subgraph_builder.compile(name="graph_patterns_specialist_subgraph")


async def _run_graph_patterns_memory_demo(
    state: DemoState,
    *,
    runtime: Runtime[RuntimeContext],
) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], {"messages": state.get("messages", [])})
    except Exception as exc:
        if _is_model_credential_error(exc):
            return {"messages": [AIMessage(content=_format_model_credential_error(exc))]}
        if _is_model_connection_error(exc):
            return {"messages": [AIMessage(content=_format_model_connection_error(exc))]}
        raise


_builder = StateGraph(MessagesState, context_schema=RuntimeContext)
_builder.add_node("load_long_term_memory", _load_long_term_memory)
_builder.add_node("human_review_gate", _human_review_gate)
_builder.add_node("execute_approved_email_action", _execute_approved_email_action)
_builder.add_node("run_specialists_subgraph", specialist_subgraph)
_builder.add_node("persist_long_term_memory", _persist_long_term_memory)
_builder.add_node("finalize", _run_graph_patterns_memory_demo)
_builder.add_edge(START, "load_long_term_memory")
_builder.add_edge("load_long_term_memory", "human_review_gate")


def _route_after_review(state: DemoState) -> str:
    if state.get("approved_email_action"):
        return "execute_approved_email_action"
    if state.get("approval_rejected"):
        return "persist_long_term_memory"
    if state.get("skip_specialists"):
        return "persist_long_term_memory"
    return "run_specialists_subgraph"


_builder.add_conditional_edges(
    "human_review_gate",
    _route_after_review,
    {
        "execute_approved_email_action": "execute_approved_email_action",
        "run_specialists_subgraph": "run_specialists_subgraph",
        "persist_long_term_memory": "persist_long_term_memory",
    },
)
_builder.add_edge("execute_approved_email_action", "persist_long_term_memory")
_builder.add_edge("run_specialists_subgraph", "persist_long_term_memory")
_builder.add_edge("persist_long_term_memory", "finalize")
_builder.add_edge("finalize", END)

graph = _builder.compile(name="graph_patterns_memory_demo")
