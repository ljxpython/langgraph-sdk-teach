from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from langchain_core.messages import ToolMessage


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from graph_src_v2.agents.graph_patterns_memory_agent import tools as gp_tools  # noqa: E402
from graph_src_v2.agents.graph_patterns_memory_agent.graph import (  # noqa: E402
    _extract_email_action,
    _extract_review_decision,
    _last_human_message_text,
    _requires_human_review,
    graph as patterns_graph,
)


def test_extract_memory_candidate_parses_supported_prefixes() -> None:
    assert gp_tools.extract_memory_candidate("记住: 我喜欢深色主题") == "我喜欢深色主题"
    assert gp_tools.extract_memory_candidate("remember: I like concise answers") == "I like concise answers"
    assert gp_tools.extract_memory_candidate("普通聊天内容") is None


def test_requires_human_review_does_not_block_memory_only_input() -> None:
    assert _requires_human_review("记住: 我偏好先灰度5%，观察10分钟再继续放量。") is False
    assert _requires_human_review("请先调用 request_human_approval 再上线") is True


def test_extract_email_action_builds_send_payload() -> None:
    action = _extract_email_action(
        "请给 ops@example.com 发邮件通知今晚灰度发布",
        {"messages": []},
    )
    assert isinstance(action, dict)
    assert action["name"] == "send_demo_email"
    assert action["args"]["to"] == ["ops@example.com"]


def test_extract_email_action_requires_recipient_when_no_history() -> None:
    action = _extract_email_action("再次发一封邮件", {"messages": []})
    assert action is None


def test_extract_email_action_reuses_recent_recipients_from_history() -> None:
    action = _extract_email_action(
        "再次发一封邮件",
        {
            "messages": [
                ToolMessage(
                    content="Email sent to ops@example.com. Subject: 系统上线通知. Body: test",
                    name="send_demo_email",
                    tool_call_id="tc-1",
                )
            ]
        },
    )
    assert isinstance(action, dict)
    assert action["name"] == "send_demo_email"
    assert action["args"]["to"] == ["ops@example.com"]


def test_extract_email_action_reuses_recipient_for_pronoun_request() -> None:
    action = _extract_email_action(
        "再帮我发一封邮件给他，说我想他了",
        {
            "messages": [
                ToolMessage(
                    content="Email sent to 1111@qq.com. Subject: 系统上线通知. Body: test",
                    name="send_demo_email",
                    tool_call_id="tc-2",
                )
            ]
        },
    )
    assert isinstance(action, dict)
    assert action["args"]["to"] == ["1111@qq.com"]


def test_extract_review_decision_is_fail_closed_for_invalid_payload() -> None:
    assert _extract_review_decision(None) is None
    assert _extract_review_decision({}) is None
    assert _extract_review_decision({"decisions": [{"type": "unexpected"}]}) is None
    assert _extract_review_decision({"decisions": [{"type": "approve"}]}) == "approve"


def test_last_human_message_text_supports_list_content() -> None:
    text = _last_human_message_text(
        cast(
            Any,
            {
                "messages": [
                    {
                        "type": "human",
                        "content": [{"type": "text", "text": "帮我发送一封邮件给1111@qq.com"}],
                    }
                ]
            },
        )
    )
    assert "1111@qq.com" in text


def test_build_multi_agent_tools_shape() -> None:
    class DummyModel:
        def bind(self, **kwargs: Any) -> Any:
            del kwargs
            return self

    demo_tools = gp_tools.build_multi_agent_tools(DummyModel())
    tool_names = {getattr(tool_obj, "name", "") for tool_obj in demo_tools}
    assert tool_names == {
        "ask_knowledge_specialist",
        "ask_ops_specialist",
    }


def test_graph_patterns_memory_demo_graph_compiles() -> None:
    assert hasattr(patterns_graph, "invoke")


def test_langgraph_registers_graph_patterns_memory_demo() -> None:
    langgraph_file = _PROJECT_ROOT / "graph_src_v2" / "langgraph.json"
    data = json.loads(langgraph_file.read_text(encoding="utf-8"))
    assert "graph_patterns_memory_demo" in data["graphs"]
