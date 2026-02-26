from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from graph_src_v2.agents.router_knowledge_base_agent import tools as kb_tools  # noqa: E402


def _invoke_tool(tool_obj: Any, args: dict[str, Any]) -> Any:
    return getattr(tool_obj, "invoke")(args)


def test_router_kb_tool_stubs() -> None:
    code = _invoke_tool(kb_tools.search_code, {"query": "auth", "repo": "main"})
    notion = _invoke_tool(kb_tools.search_notion, {"query": "api auth"})
    slack = _invoke_tool(kb_tools.search_slack, {"query": "token refresh"})
    assert "auth middleware" in code
    assert "Notion docs" in notion
    assert "Slack results" in slack


def test_router_kb_workflow_compiles() -> None:
    class DummyModel:
        def bind(self, **kwargs: Any) -> Any:
            del kwargs
            return self

        def with_structured_output(self, schema: Any) -> Any:
            del schema

            class _Structured:
                @staticmethod
                def invoke(_messages: list[dict[str, str]]) -> Any:
                    return kb_tools.ClassificationResult(
                        classifications=[{"source": "github", "query": "search auth code"}]
                    )

            return _Structured()

        def invoke(self, _messages: list[dict[str, str]]) -> Any:
            class _Msg:
                content = "synthetic answer"

            return _Msg()

    workflow = kb_tools.build_router_workflow(DummyModel())
    assert hasattr(workflow, "invoke")


def test_langgraph_registers_router_knowledge_base_demo() -> None:
    langgraph_file = _PROJECT_ROOT / "graph_src_v2" / "langgraph.json"
    data = json.loads(langgraph_file.read_text(encoding="utf-8"))
    assert "router_knowledge_base_demo" in data["graphs"]
