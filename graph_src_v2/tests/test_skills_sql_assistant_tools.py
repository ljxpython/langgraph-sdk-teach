from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from graph_src_v2.agents.skills_sql_assistant_agent import tools as sql_tools  # noqa: E402


def _invoke_tool(tool_obj: Any, args: dict[str, Any]) -> Any:
    return getattr(tool_obj, "invoke")(args)


def test_load_skill_sales_analytics() -> None:
    text = _invoke_tool(sql_tools.load_skill, {"skill_name": "sales_analytics"})
    assert "Loaded skill: sales_analytics" in text
    assert "customers" in text
    assert "orders" in text


def test_load_skill_unknown() -> None:
    text = _invoke_tool(sql_tools.load_skill, {"skill_name": "unknown_skill"})
    assert "not found" in text
    assert "sales_analytics" in text
    assert "inventory_management" in text


def test_skill_middleware_registers_load_tool() -> None:
    middleware = sql_tools.SkillMiddleware()
    assert sql_tools.load_skill in middleware.tools


def test_build_skills_sql_assistant_agent_runnable() -> None:
    class DummyModel:
        def bind(self, **kwargs: Any) -> Any:
            del kwargs
            return self

    agent = sql_tools.build_skills_sql_assistant_agent(DummyModel())
    assert hasattr(agent, "invoke")


def test_langgraph_registers_skills_sql_assistant_demo() -> None:
    langgraph_file = _PROJECT_ROOT / "graph_src_v2" / "langgraph.json"
    data = json.loads(langgraph_file.read_text(encoding="utf-8"))
    assert "skills_sql_assistant_demo" in data["graphs"]
