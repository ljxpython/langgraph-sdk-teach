from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from fastapi_src.api.routes import create_router
from fastapi_src.core.config import Settings
from fastapi_src.db.sqlite import init_db
from fastapi_src.repositories.run_log_repo import RunLogRepository
from fastapi_src.repositories.thread_repo import ThreadRepository
from fastapi_src.services.chat_service import ChatService


class _FakeBackend:
    def __init__(self) -> None:
        self.thread_seq = 0
        self.run_seq = 0
        self.fail_next_stream = False
        self.messages_by_thread: dict[str, list[dict[str, Any]]] = {}

    def new_thread_id(self) -> str:
        self.thread_seq += 1
        return f"thread-{self.thread_seq}"

    def new_run_id(self) -> str:
        self.run_seq += 1
        return f"run-{self.run_seq}"


class _FakeThreads:
    def __init__(self, backend: _FakeBackend) -> None:
        self._backend = backend

    async def create(self) -> dict[str, str]:
        thread_id = self._backend.new_thread_id()
        self._backend.messages_by_thread.setdefault(thread_id, [])
        return {"thread_id": thread_id}

    async def get_state(self, thread_id: str) -> dict[str, Any]:
        messages = self._backend.messages_by_thread.get(thread_id, [])
        return {"values": {"messages": messages}}


class _FakeRuns:
    def __init__(self, backend: _FakeBackend) -> None:
        self._backend = backend

    async def wait(
        self,
        thread_id: str,
        assistant_id: str,
        *,
        input: dict[str, Any] | None,
        context: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        command: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = self._backend.new_run_id()
        user_content = str(input["messages"][0]["content"]) if input and input.get("messages") else ""
        ai_text = f"ok:{assistant_id}"
        messages = [
            {"type": "human", "content": user_content},
            {"type": "ai", "content": ai_text},
        ]
        self._backend.messages_by_thread.setdefault(thread_id, []).extend(messages)
        return {"run_id": run_id, "messages": messages}

    async def stream(
        self,
        thread_id: str,
        assistant_id: str,
        *,
        input: dict[str, Any],
        context: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        stream_mode: list[str] | None = None,
    ):
        if self._backend.fail_next_stream:
            self._backend.fail_next_stream = False
            raise RuntimeError("stream failed")

        yield SimpleNamespace(event="messages/partial", data={"type": "ai", "content": "part"})
        yield SimpleNamespace(event="updates", data={"node": "agent"})


class _FakeClient:
    def __init__(self, backend: _FakeBackend) -> None:
        self.threads = _FakeThreads(backend)
        self.runs = _FakeRuns(backend)


def _build_test_client(tmp_path: Any, monkeypatch: Any) -> tuple[TestClient, _FakeBackend, RunLogRepository]:
    db_path = str(tmp_path / "app.db")
    init_db(db_path)

    settings = Settings(
        langgraph_api_url="http://127.0.0.1:8123",
        default_assistant_id="agent",
        sqlite_path=db_path,
        default_stream_mode="messages,updates,tasks,checkpoints,debug",
        cors_origins=["http://127.0.0.1:5173"],
    )
    repo = ThreadRepository(db_path)
    run_log_repo = RunLogRepository(db_path)
    service = ChatService(repo, settings, run_log_repo=run_log_repo)

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=None,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(create_router(service))

    backend = _FakeBackend()
    fake_client = _FakeClient(backend)
    monkeypatch.setattr("fastapi_src.services.chat_service.get_langgraph_client", lambda _: fake_client)
    monkeypatch.setattr("fastapi_src.api.routes.get_langgraph_client", lambda _: fake_client)

    return TestClient(app), backend, run_log_repo


def test_thread_create_or_reuse(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    first = client.post("/api/thread", json={"user_id": "u-1"})
    assert first.status_code == 200
    first_json = first.json()
    assert first_json["created"] is True

    second = client.post("/api/thread", json={"user_id": "u-1"})
    assert second.status_code == 200
    second_json = second.json()
    assert second_json["created"] is False
    assert second_json["thread_id"] == first_json["thread_id"]


def test_wait_and_state_roundtrip(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, run_log_repo = _build_test_client(tmp_path, monkeypatch)

    wait_resp = client.post(
        "/api/chat/wait",
        json={"user_id": "u-2", "message": "hello", "assistant_id": "agent"},
    )
    assert wait_resp.status_code == 200
    wait_json = wait_resp.json()
    assert "thread_id" in wait_json
    assert wait_json["result"]["messages"][-1]["type"] == "ai"

    state_resp = client.get("/api/state", params={"user_id": "u-2"})
    assert state_resp.status_code == 200
    state_json = state_resp.json()
    contents = [m.get("content", "") for m in state_json["state"]["values"]["messages"]]
    assert any("hello" in text for text in contents)

    logs = run_log_repo.list_by_user("u-2")
    assert any(item["endpoint"] == "/api/chat/wait" and item["status"] == "success" for item in logs)


def test_stream_passthrough_and_done_event(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, run_log_repo = _build_test_client(tmp_path, monkeypatch)

    with client.stream(
        "GET",
        "/api/chat/stream",
        params={"user_id": "u-3", "assistant_id": "agent", "message": "ping"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "event: messages/partial" in body
    assert "event: updates" in body
    assert "event: done" in body

    logs = run_log_repo.list_by_user("u-3")
    assert any(item["event"] == "messages/partial" for item in logs)
    assert any(item["event"] == "done" and item["status"] == "done" for item in logs)


def test_resume_chat_and_log(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, run_log_repo = _build_test_client(tmp_path, monkeypatch)

    create_resp = client.post("/api/thread", json={"user_id": "u-resume"})
    assert create_resp.status_code == 200

    resume_resp = client.post(
        "/api/chat/resume",
        json={
            "user_id": "u-resume",
            "assistant_id": "deepagent_demo",
            "command": {"resume": {"decisions": [{"type": "approve"}]}},
        },
    )
    assert resume_resp.status_code == 200
    payload = resume_resp.json()
    assert payload["thread_id"].startswith("thread-")
    assert payload["result"]["messages"][-1]["type"] == "ai"

    logs = run_log_repo.list_by_user("u-resume")
    assert any(item["endpoint"] == "/api/chat/resume" and item["event"] == "resume" for item in logs)


def test_run_logs_endpoint(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    wait_resp = client.post(
        "/api/chat/wait",
        json={"user_id": "u-log", "message": "hello", "assistant_id": "agent"},
    )
    assert wait_resp.status_code == 200

    logs_resp = client.get("/api/run-logs", params={"user_id": "u-log"})
    assert logs_resp.status_code == 200
    payload = logs_resp.json()
    assert payload["user_id"] == "u-log"
    assert isinstance(payload["items"], list)
    assert any(item.get("endpoint") == "/api/chat/wait" for item in payload["items"])


def test_stream_invalid_context_json_returns_400(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.get(
        "/api/chat/stream",
        params={
            "user_id": "u-4",
            "assistant_id": "agent",
            "message": "ping",
            "context_json": "{invalid",
        },
    )
    assert resp.status_code == 400
    assert "context_json" in resp.text


def test_stream_error_event_and_log(tmp_path: Any, monkeypatch: Any) -> None:
    client, backend, run_log_repo = _build_test_client(tmp_path, monkeypatch)
    backend.fail_next_stream = True

    with client.stream(
        "GET",
        "/api/chat/stream",
        params={"user_id": "u-5", "assistant_id": "agent", "message": "ping"},
    ) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())

    assert "event: error" in body

    logs = run_log_repo.list_by_user("u-5")
    assert any(item["event"] == "error" and item["status"] == "error" for item in logs)


def test_state_without_thread_returns_404(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.get("/api/state", params={"user_id": "missing-user"})
    assert resp.status_code == 404


def test_cors_preflight_allows_localhost_origin(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.options(
        "/api/thread",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") in {"*", "http://localhost:5173"}
