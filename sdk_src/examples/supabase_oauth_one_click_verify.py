from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from langgraph_sdk import get_client
from dotenv import load_dotenv


def _load_env_file() -> None:
    current = Path(__file__).resolve()
    root = current.parents[2]
    load_dotenv(root / ".env", override=False)
    load_dotenv(override=False)


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-click Supabase OAuth verification")
    parser.add_argument("--api-url", default="http://127.0.0.1:8123")
    parser.add_argument("--graph-id", default="agent")
    parser.add_argument("--user-email", default="user1@example.com")
    parser.add_argument("--viewer-email", default="user2@example.com")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--promote-user-to-admin", action="store_true")
    return parser.parse_args()


async def _login(supabase_url: str, anon_key: str, email: str, password: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
            headers={"apikey": anon_key, "Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def _get_admin_user(supabase_url: str, service_key: str, user_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{supabase_url}/auth/v1/admin/users/{user_id}",
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        )
        response.raise_for_status()
        return response.json()


async def _set_role(supabase_url: str, service_key: str, user_id: str, role: str) -> None:
    existing = await _get_admin_user(supabase_url, service_key, user_id)
    app_metadata = dict(existing.get("app_metadata") or {})
    app_metadata["role"] = role
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.put(
            f"{supabase_url}/auth/v1/admin/users/{user_id}",
            json={"app_metadata": app_metadata},
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()


async def _expect_ok(step: str, awaitable: Any) -> Any:
    try:
        result = await awaitable
        print(f"[PASS] {step}")
        return result
    except Exception as exc:
        print(f"[FAIL] {step}: {exc}")
        raise


async def _expect_denied(step: str, awaitable: Any, codes: set[int]) -> None:
    try:
        await awaitable
        raise AssertionError(f"Expected denial for {step}")
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if isinstance(status, int) and status in codes:
            print(f"[PASS] {step} denied status={status}")
            return
        print(f"[FAIL] {step} expected denied codes={sorted(codes)}, got={status}, error={exc}")
        raise


async def _run() -> None:
    _load_env_file()
    args = _parse_args()
    supabase_url = _env("SUPABASE_URL")
    anon_key = _env("SUPABASE_ANON_KEY")
    service_key = _env("SUPABASE_SERVICE_KEY")

    user_session = await _login(supabase_url, anon_key, args.user_email, args.password)
    viewer_session = await _login(supabase_url, anon_key, args.viewer_email, args.password)
    user_id = user_session["user"]["id"]
    viewer_id = viewer_session["user"]["id"]
    print(f"user_id={user_id}")
    print(f"viewer_id={viewer_id}")

    await _set_role(supabase_url, service_key, user_id, "user")
    await _set_role(supabase_url, service_key, viewer_id, "viewer")

    user_token = (await _login(supabase_url, anon_key, args.user_email, args.password))["access_token"]
    viewer_token = (await _login(supabase_url, anon_key, args.viewer_email, args.password))["access_token"]

    user_client = get_client(url=args.api_url, headers={"Authorization": f"Bearer {user_token}"})
    viewer_client = get_client(url=args.api_url, headers={"Authorization": f"Bearer {viewer_token}"})

    thread = await _expect_ok("user can create thread", user_client.threads.create())
    await _expect_denied("viewer cannot create thread", viewer_client.threads.create(), {403})
    await _expect_denied(
        "viewer cannot read user thread",
        viewer_client.threads.get(thread["thread_id"]),
        {403, 404},
    )
    await _expect_ok("user can search assistants", user_client.assistants.search(limit=5, offset=0))
    await _expect_denied(
        "user cannot create assistant",
        user_client.assistants.create(args.graph_id, name="one-click-should-deny"),
        {403},
    )

    if args.promote_user_to_admin:
        await _set_role(supabase_url, service_key, user_id, "admin")
        admin_token = (await _login(supabase_url, anon_key, args.user_email, args.password))["access_token"]
        admin_client = get_client(url=args.api_url, headers={"Authorization": f"Bearer {admin_token}"})
        created = await _expect_ok(
            "admin can create assistant",
            admin_client.assistants.create(args.graph_id, name="one-click-admin-check"),
        )
        await _expect_ok(
            "admin can delete assistant",
            admin_client.assistants.delete(created["assistant_id"], delete_threads=False),
        )

    print("ALL_ONE_CLICK_CHECKS_PASSED")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
