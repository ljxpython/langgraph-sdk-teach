from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool

from graph_src_v2.agents.graph_patterns_memory_agent.prompts import (
    KNOWLEDGE_SPECIALIST_PROMPT,
    OPS_SPECIALIST_PROMPT,
)


def message_to_text(message: Any) -> str:
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


def extract_memory_candidate(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    prefixes = ["记住:", "记住：", "remember:", "remember "]
    lowered = stripped.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix.lower()):
            candidate = stripped[len(prefix) :].strip()
            return candidate or None
    return None


@tool("lookup_internal_knowledge", description="Search internal engineering notes for a topic.")
def lookup_internal_knowledge(topic: str) -> str:
    return (
        f"Knowledge note for '{topic}': keep workflows deterministic where possible and use "
        "tool output as structured evidence."
    )


@tool("draft_release_plan", description="Create a practical release and rollback plan.")
def draft_release_plan(feature: str, risk_level: str = "medium") -> str:
    return (
        f"Release plan for '{feature}' (risk={risk_level}): "
        "1) 5% canary, 2) monitor SLOs, 3) rollback on error spike."
    )


@tool("send_demo_email", description="Send an operations update email to stakeholders.")
def send_demo_email(to: list[str], subject: str, body: str) -> str:
    recipients = ", ".join(to)
    return f"Email sent to {recipients}. Subject: {subject}. Body: {body}"


@tool(
    "request_human_approval",
    description=(
        "Create a human review checkpoint before high-impact actions. "
        "HumanInTheLoopMiddleware will interrupt and request approve/edit/reject decisions."
    ),
)
def request_human_approval(action: str, details: str) -> str:
    return f"Approval checkpoint requested for action='{action}' with details='{details}'."


def build_multi_agent_tools(model: Any) -> list[Any]:
    knowledge_specialist = create_agent(
        model=model,
        tools=[lookup_internal_knowledge],
        system_prompt=KNOWLEDGE_SPECIALIST_PROMPT,
        name="graph_patterns_knowledge_specialist",
    )
    ops_specialist = create_agent(
        model=model,
        tools=[draft_release_plan],
        system_prompt=OPS_SPECIALIST_PROMPT,
        name="graph_patterns_ops_specialist",
    )

    @tool(
        "ask_knowledge_specialist",
        description="Delegate implementation analysis to the knowledge specialist sub-agent.",
    )
    def ask_knowledge_specialist(request: str) -> str:
        result = knowledge_specialist.invoke({"messages": [{"role": "user", "content": request}]})
        return message_to_text(result["messages"][-1])

    @tool(
        "ask_ops_specialist",
        description="Delegate rollout planning to the operations specialist sub-agent.",
    )
    def ask_ops_specialist(request: str) -> str:
        result = ops_specialist.invoke({"messages": [{"role": "user", "content": request}]})
        return message_to_text(result["messages"][-1])

    return [
        ask_knowledge_specialist,
        ask_ops_specialist,
    ]
