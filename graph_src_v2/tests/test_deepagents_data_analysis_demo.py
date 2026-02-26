from __future__ import annotations

import json
import sys
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from graph_src_v2.agents.deepagents_data_analysis_agent.prompts import SYSTEM_PROMPT  # noqa: E402


def test_data_analysis_prompt_disables_slack_delivery() -> None:
    assert "Do not use Slack" in SYSTEM_PROMPT


def test_langgraph_registers_deepagents_data_analysis_demo() -> None:
    langgraph_file = _PROJECT_ROOT / "graph_src_v2" / "langgraph.json"
    data = json.loads(langgraph_file.read_text(encoding="utf-8"))
    assert "deepagents_data_analysis_demo" in data["graphs"]
