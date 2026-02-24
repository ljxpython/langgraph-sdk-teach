from __future__ import annotations

from sdk_src.examples.langgraph_sdk_learn_common import build_client_headers


def test_build_client_headers_with_api_key() -> None:
    headers = build_client_headers("owner-key", None)
    assert headers == {"x-api-key": "owner-key"}


def test_build_client_headers_with_bearer() -> None:
    headers = build_client_headers(None, "owner-token")
    assert headers == {"Authorization": "Bearer owner-token"}


def test_build_client_headers_rejects_dual_auth() -> None:
    try:
        build_client_headers("owner-key", "owner-token")
    except ValueError as exc:
        assert "不能同时" in str(exc)
    else:
        raise AssertionError("Expected ValueError when both auth args are set")
