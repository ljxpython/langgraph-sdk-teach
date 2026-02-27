from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool

from graph_src_v2.agents.assistant_agent.prompts import (
    EMAIL_SPECIALIST_PROMPT,
    KNOWLEDGE_SPECIALIST_PROMPT,
    OPS_SPECIALIST_PROMPT,
)
from graph_src_v2.runtime.options import AppRuntimeConfig
from graph_src_v2.tools.registry import build_tools


async def build_assistant_tools(options: AppRuntimeConfig) -> list[Any]:
    return await build_tools(options)


def _message_to_text(message: Any) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                maybe = item.get("text")
                if isinstance(maybe, str) and maybe:
                    parts.append(maybe)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(message)


def _extract_agent_reply(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    if not messages:
        return "Specialist agent returned no message."
    return _message_to_text(messages[-1])


@tool("lookup_internal_knowledge", description="Search internal implementation notes for a given topic.")
def lookup_internal_knowledge(topic: str) -> str:
    return (
        f"Knowledge note for '{topic}': use model-bound tools for deterministic actions, "
        "and keep user-facing summaries concise."
    )


@tool("draft_release_plan", description="Draft a rollout plan and risk controls for a feature release.")
def draft_release_plan(feature: str, risk_level: str = "medium") -> str:
    return (
        f"Release plan for '{feature}' (risk={risk_level}): "
        "1) canary rollout, 2) monitor error budget, 3) prepare rollback switch."
    )


@tool("send_demo_email", description="Draft and send a stakeholder email for a rollout update.")
def send_demo_email(to: list[str], subject: str, body: str) -> str:
    recipients = ", ".join(to)
    return f"Email sent to {recipients}. Subject: {subject}. Body: {body}"


def build_langchain_concepts_demo_tools(model: Any) -> list[Any]:
    knowledge_specialist = create_agent(
        model=model,
        tools=[lookup_internal_knowledge],
        system_prompt=KNOWLEDGE_SPECIALIST_PROMPT,
        name="assistant_knowledge_specialist",
    )
    ops_specialist = create_agent(
        model=model,
        tools=[draft_release_plan],
        system_prompt=OPS_SPECIALIST_PROMPT,
        name="assistant_ops_specialist",
    )
    email_specialist = create_agent(
        model=model,
        tools=[send_demo_email],
        system_prompt=EMAIL_SPECIALIST_PROMPT,
        name="assistant_email_specialist",
    )

    @tool(
        "ask_knowledge_specialist",
        description="Delegate implementation Q&A to the knowledge specialist sub-agent.",
    )
    def ask_knowledge_specialist(request: str) -> str:
        result = knowledge_specialist.invoke({"messages": [{"role": "user", "content": request}]})
        return _extract_agent_reply(result)

    @tool(
        "ask_ops_specialist",
        description="Delegate rollout and reliability planning to the operations specialist sub-agent.",
    )
    def ask_ops_specialist(request: str) -> str:
        result = ops_specialist.invoke({"messages": [{"role": "user", "content": request}]})
        return _extract_agent_reply(result)

    @tool(
        "ask_email_specialist",
        description="Delegate stakeholder communication drafting to the email specialist sub-agent.",
    )
    def ask_email_specialist(request: str) -> str:
        result = email_specialist.invoke({"messages": [{"role": "user", "content": request}]})
        return _extract_agent_reply(result)

    @tool(
        "request_human_approval",
        description=(
            "Create a human-review checkpoint before high-impact actions. "
            "This tool is guarded by HumanInTheLoopMiddleware and will interrupt execution for review."
        ),
    )
    def request_human_approval(action: str, details: str) -> str:
        return (
            "Approval checkpoint reached. "
            f"Action='{action}', details='{details}'. If you see this message, review approved execution."
        )

    return [
        ask_knowledge_specialist,
        ask_ops_specialist,
        ask_email_specialist,
        request_human_approval,
    ]
