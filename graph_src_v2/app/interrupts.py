from __future__ import annotations

from typing import Any, Mapping

from langgraph.types import Command


def normalize_hitl_interrupt(result: Mapping[str, Any]) -> dict[str, Any]:
    interrupts = result.get("__interrupt__")
    if not isinstance(interrupts, list) or not interrupts:
        return {
            "interrupted": False,
            "action_requests": [],
            "resume_payload_example": None,
        }

    first = interrupts[0]
    value = getattr(first, "value", None)
    payload = value if isinstance(value, Mapping) else {}
    action_requests = payload.get("action_requests")
    review_configs = payload.get("review_configs")
    if not isinstance(action_requests, list):
        action_requests = []
    if not isinstance(review_configs, list):
        review_configs = []

    config_by_action_name: dict[str, Mapping[str, Any]] = {}
    for item in review_configs:
        mapping = item if isinstance(item, Mapping) else {}
        action_name = mapping.get("action_name")
        if isinstance(action_name, str) and action_name:
            config_by_action_name[action_name] = mapping

    normalized: list[dict[str, Any]] = []
    for req in action_requests:
        req_map = req if isinstance(req, Mapping) else {}
        name = req_map.get("name")
        args = req_map.get("args")
        cfg = config_by_action_name.get(name, {}) if isinstance(name, str) else {}
        allowed = cfg.get("allowed_decisions")
        allowed_decisions = allowed if isinstance(allowed, list) else []
        normalized.append(
            {
                "tool_name": name if isinstance(name, str) else "",
                "args": args if isinstance(args, Mapping) else args,
                "allowed_decisions": allowed_decisions,
            }
        )

    resume_payload_example = {
        "decisions": [{"type": "approve"} for _ in normalized],
    }

    return {
        "interrupted": True,
        "action_requests": normalized,
        "resume_payload_example": resume_payload_example,
    }


def build_resume_command(decisions: list[dict[str, Any]]) -> Command:
    return Command(resume={"decisions": decisions})
