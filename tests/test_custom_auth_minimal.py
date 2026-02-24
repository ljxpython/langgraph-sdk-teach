from __future__ import annotations

import asyncio

from graph_src.auth import (
    _extract_token,
    _resolve_user,
    apply_thread_owner,
    authenticate,
    ensure_assistant_write_allowed,
    ensure_permission,
    ensure_store_namespace_allowed,
    thread_owner_filter,
)


def test_extract_bearer_token() -> None:
    token = _extract_token({"authorization": "Bearer owner-token"})
    assert token == "owner-token"


def test_extract_api_key_token() -> None:
    token = _extract_token({b"x-api-key": b"viewer-key"})
    assert token == "viewer-token"


def test_authenticate_invalid_token_raises_401() -> None:
    try:
        asyncio.run(authenticate({"authorization": "Bearer invalid"}))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401
        assert "Invalid credentials" in str(getattr(exc, "detail", ""))
    else:
        raise AssertionError("Expected 401 error for invalid token")


def test_permission_denied_raises_403() -> None:
    user = _resolve_user("viewer-token")
    try:
        ensure_permission(user, "threads", "create")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("Expected 403 error for missing permission")


def test_apply_thread_owner_sets_metadata() -> None:
    user = _resolve_user("owner-token")
    payload = {"metadata": {"topic": "demo"}}
    updated = apply_thread_owner(payload, user)
    assert updated["metadata"]["owner"] == "owner_user"
    assert updated["metadata"]["topic"] == "demo"


def test_thread_owner_filter_for_admin() -> None:
    admin = _resolve_user("admin-token")
    assert thread_owner_filter(admin) == {}


def test_owner_can_read_assistants() -> None:
    owner = _resolve_user("owner-token")
    ensure_permission(owner, "assistants", "read")


def test_owner_cannot_write_assistants() -> None:
    owner = _resolve_user("owner-token")
    try:
        ensure_assistant_write_allowed(owner)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("Expected 403 for non-admin assistant write")


def test_admin_can_write_assistants() -> None:
    admin = _resolve_user("admin-token")
    ensure_assistant_write_allowed(admin)


def test_owner_can_create_run_on_threads() -> None:
    owner = _resolve_user("owner-token")
    ensure_permission(owner, "threads", "create_run")


def test_viewer_can_create_run_on_threads() -> None:
    viewer = _resolve_user("viewer-token")
    ensure_permission(viewer, "threads", "create_run")


def test_owner_store_namespace_allowed() -> None:
    owner = _resolve_user("owner-token")
    ensure_store_namespace_allowed(owner, ("owner_user", "memory", "item-1"))


def test_owner_store_namespace_denied_cross_user() -> None:
    owner = _resolve_user("owner-token")
    try:
        ensure_store_namespace_allowed(owner, ("viewer_user", "memory", "item-1"))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("Expected 403 for cross-user store namespace")


def test_admin_store_namespace_can_cross_user() -> None:
    admin = _resolve_user("admin-token")
    ensure_store_namespace_allowed(admin, ("owner_user", "memory", "item-1"))
