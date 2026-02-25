from __future__ import annotations

import pytest

pytest.importorskip("deepagents")

from graph_src_v1.agents.deepagent_agent.graph import (
    _resolve_skills,
    _resolve_subagents,
    _resolve_system_prompt,
)
from graph_src_v1.agents.deepagent_agent.prompts import SYSTEM_PROMPT
from graph_src_v1.config.runtime import DEFAULT_SYSTEM_PROMPT


def test_resolve_skills_prefers_context_over_configurable() -> None:
    context = {"skills": ["/skills/common", "/skills/custom"]}
    configurable = {"skills": ["/skills/config-only"]}
    assert _resolve_skills(context, configurable) == ["/skills/common", "/skills/custom"]


def test_resolve_subagents_accepts_mapping_payload() -> None:
    context = {
        "subagents": [
            {
                "name": "qa-subagent",
                "description": "quality reviewer",
                "system_prompt": "Review outputs carefully",
                "skills": ["/skills/research"],
            }
        ]
    }
    resolved = _resolve_subagents(context, {})
    assert len(resolved) == 1
    assert resolved[0]["name"] == "qa-subagent"


def test_resolve_system_prompt_falls_back_to_deepagent_default() -> None:
    assert _resolve_system_prompt({}, {}, DEFAULT_SYSTEM_PROMPT) == SYSTEM_PROMPT
