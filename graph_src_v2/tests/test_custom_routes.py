from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from graph_src_v2.custom_routes.app import app  # noqa: E402


def test_list_tools_route() -> None:
    client = TestClient(app)
    response = client.get("/internal/capabilities/tools")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    names = [item["name"] for item in payload["tools"]]
    assert "word_count" in names
    assert "to_upper" in names


def test_list_mcp_servers_route() -> None:
    client = TestClient(app)
    response = client.get("/internal/capabilities/mcp-servers")
    assert response.status_code == 200
    payload = response.json()
    names = [item["name"] for item in payload["servers"]]
    assert "local_math" in names
    assert "local_text" in names


def test_resolve_defaults_disabled() -> None:
    client = TestClient(app)
    response = client.post("/internal/capabilities/resolve", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["enable_local_tools"] is False
    assert payload["enable_local_mcp"] is False
    assert payload["local_tools"] == []
    assert payload["mcp_servers"] == []


def test_resolve_selected_tools_and_mcp() -> None:
    client = TestClient(app)
    response = client.post(
        "/internal/capabilities/resolve",
        json={
            "enable_local_tools": True,
            "local_tools": ["word_count", "to_upper"],
            "enable_local_mcp": True,
            "mcp_servers": ["local_text"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload["local_tools"]] == ["word_count", "to_upper"]
    assert [item["name"] for item in payload["mcp_servers"]] == ["local_text"]


def test_resolve_rejects_unknown_names() -> None:
    client = TestClient(app)
    response = client.post(
        "/internal/capabilities/resolve",
        json={
            "enable_local_tools": True,
            "local_tools": ["bad_tool"],
        },
    )
    assert response.status_code == 400
