from __future__ import annotations

import argparse
import asyncio
import uuid
from typing import Any

from langgraph_sdk import get_client


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _status_of_error(exc: Exception) -> int | None:
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


async def _expect_success(step: str, coro: Any) -> Any:
    try:
        result = await coro
        print(f"[PASS] {step}")
        return result
    except Exception as exc:
        print(f"[FAIL] {step} -> unexpected error: {exc}")
        raise


async def _expect_denied(step: str, coro: Any, allowed_codes: set[int]) -> None:
    try:
        await coro
    except Exception as exc:
        status = _status_of_error(exc)
        if status in allowed_codes:
            print(f"[PASS] {step} -> denied as expected (status={status})")
            return
        print(f"[FAIL] {step} -> denied with unexpected status={status}, error={exc}")
        raise
    print(f"[FAIL] {step} -> expected denial but request succeeded")
    raise AssertionError(step)


async def run_demo(url: str, graph_id: str) -> None:
    owner = get_client(url=url, headers=_headers("owner-token"))
    viewer = get_client(url=url, headers=_headers("viewer-token"))
    admin = get_client(url=url, headers=_headers("admin-token"))

    created_assistant_id: str | None = None

    print("=== Stage B live demo start ===")
    print(f"url={url} graph_id={graph_id}")

    await _expect_success("owner assistants.search", owner.assistants.search(limit=5, offset=0))

    await _expect_denied(
        "owner assistants.create denied",
        owner.assistants.create(graph_id, name=f"owner-denied-{uuid.uuid4().hex[:6]}"),
        {403},
    )

    assistant = await _expect_success(
        "admin assistants.create",
        admin.assistants.create(graph_id, name=f"admin-stage-b-{uuid.uuid4().hex[:6]}"),
    )
    created_assistant_id = assistant["assistant_id"]
    print(f"created_assistant_id={created_assistant_id}")

    await _expect_denied(
        "viewer assistants.create denied",
        viewer.assistants.create(graph_id, name=f"viewer-denied-{uuid.uuid4().hex[:6]}"),
        {403},
    )

    owner_thread = await _expect_success("owner threads.create", owner.threads.create())
    print(f"owner_thread_id={owner_thread['thread_id']}")
    await _expect_denied("viewer threads.create denied", viewer.threads.create(), {403})

    await _expect_denied("viewer cannot read owner thread", viewer.threads.get(owner_thread["thread_id"]), {403, 404})

    if created_assistant_id is not None:
        await _expect_success("admin assistants.delete", admin.assistants.delete(created_assistant_id, delete_threads=False))

    print("=== Stage B live demo completed ===")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage B auth rules live demo")
    parser.add_argument("--url", default="http://127.0.0.1:8123", help="LangGraph API URL")
    parser.add_argument("--graph-id", default="agent", help="Graph ID used for assistants.create")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    asyncio.run(run_demo(url=args.url, graph_id=args.graph_id))


if __name__ == "__main__":
    main()
