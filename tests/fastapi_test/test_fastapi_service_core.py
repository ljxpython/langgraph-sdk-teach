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
        self.last_wait_context: dict[str, Any] | None = None
        self.last_wait_config: dict[str, Any] | None = None
        self.last_stream_context: dict[str, Any] | None = None
        self.last_stream_config: dict[str, Any] | None = None

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

    async def get(self, thread_id: str) -> dict[str, str]:
        if thread_id not in self._backend.messages_by_thread:
            raise RuntimeError("Thread or assistant not found")
        return {"thread_id": thread_id}

    async def get_state(self, thread_id: str) -> dict[str, Any]:
        messages = self._backend.messages_by_thread.get(thread_id, [])
        return {"values": {"messages": messages}}

    async def get_history(self, thread_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        messages = self._backend.messages_by_thread.get(thread_id, [])
        return [{"checkpoint": "cp-1", "values": {"messages": messages[-limit:]}}]


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
        self._backend.last_wait_context = context
        self._backend.last_wait_config = config
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
        self._backend.last_stream_context = context
        self._backend.last_stream_config = config
        if self._backend.fail_next_stream:
            self._backend.fail_next_stream = False
            raise RuntimeError("stream failed")

        yield SimpleNamespace(event="messages/partial", data={"type": "ai", "content": "part"})
        yield SimpleNamespace(event="updates", data={"node": "agent"})


class _FakeAssistants:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {
            "agent": {"assistant_id": "agent", "graph_id": "agent", "name": "Default Agent"},
            "deepagent_demo": {
                "assistant_id": "deepagent_demo",
                "graph_id": "deepagent_demo",
                "name": "DeepAgent Demo",
            },
        }
        self._seq = 0

    async def search(self, *, limit: int = 10, offset: int = 0, graph_id: str | None = None) -> list[dict[str, Any]]:
        items = list(self._items.values())
        if graph_id:
            items = [item for item in items if item["graph_id"] == graph_id]
        items.sort(key=lambda item: item["assistant_id"])
        return items[offset : offset + limit]

    async def get(self, assistant_id: str) -> dict[str, Any]:
        if assistant_id not in self._items:
            raise RuntimeError("Assistant not found")
        return dict(self._items[assistant_id])

    async def create(
        self,
        graph_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._seq += 1
        assistant_id = f"asst-{self._seq}"
        item = {
            "assistant_id": assistant_id,
            "graph_id": graph_id,
            "name": name,
            "description": description,
            "config": config,
            "context": context,
            "metadata": metadata,
        }
        self._items[assistant_id] = item
        return dict(item)

    async def update(
        self,
        assistant_id: str,
        *,
        graph_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if assistant_id not in self._items:
            raise RuntimeError("Assistant not found")
        current = dict(self._items[assistant_id])
        if graph_id is not None:
            current["graph_id"] = graph_id
        if name is not None:
            current["name"] = name
        if description is not None:
            current["description"] = description
        if config is not None:
            current["config"] = config
        if context is not None:
            current["context"] = context
        if metadata is not None:
            current["metadata"] = metadata
        self._items[assistant_id] = current
        return dict(current)

    async def delete(self, assistant_id: str, *, delete_threads: bool = False) -> None:
        _ = delete_threads
        if assistant_id not in self._items:
            raise RuntimeError("Assistant not found")
        self._items.pop(assistant_id, None)


class _FakeClient:
    def __init__(self, backend: _FakeBackend) -> None:
        self.threads = _FakeThreads(backend)
        self.runs = _FakeRuns(backend)
        self.assistants = _FakeAssistants()


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

    wait_resp_2 = client.post(
        "/api/chat/wait",
        json={"user_id": "u-2", "message": "hello again", "assistant_id": "agent"},
    )
    assert wait_resp_2.status_code == 200
    assert wait_resp_2.json()["thread_id"] == wait_json["thread_id"]

    state_resp = client.get("/api/state", params={"user_id": "u-2"})
    assert state_resp.status_code == 200
    state_json = state_resp.json()
    contents = [m.get("content", "") for m in state_json["state"]["values"]["messages"]]
    assert any("hello" in text for text in contents)

    logs = run_log_repo.list_by_user("u-2")
    assert any(item["endpoint"] == "/api/chat/wait" and item["status"] == "success" for item in logs)


def test_messages_and_history_endpoints(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    wait_resp = client.post(
        "/api/chat/wait",
        json={"user_id": "u-msg", "message": "hello message", "assistant_id": "agent"},
    )
    assert wait_resp.status_code == 200

    messages_resp = client.get("/api/messages", params={"user_id": "u-msg", "limit": 50})
    assert messages_resp.status_code == 200
    messages_payload = messages_resp.json()
    assert messages_payload["thread_id"].startswith("thread-")
    assert isinstance(messages_payload["items"], list)
    assert any(item.get("role") == "user" and "hello message" in item.get("text", "") for item in messages_payload["items"])

    paged_resp = client.get("/api/messages", params={"user_id": "u-msg", "limit": 1, "offset": 1})
    assert paged_resp.status_code == 200
    paged_items = paged_resp.json()["items"]
    assert len(paged_items) == 1

    history_resp = client.get("/api/history", params={"user_id": "u-msg", "limit": 5})
    assert history_resp.status_code == 200
    history_payload = history_resp.json()
    assert history_payload["thread_id"].startswith("thread-")
    assert isinstance(history_payload["items"], list)


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


def test_resume_requires_thread_or_user(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.post(
        "/api/chat/resume",
        json={
            "assistant_id": "deepagent_demo",
            "command": {"resume": {"decisions": [{"type": "approve"}]}},
        },
    )
    assert resp.status_code == 400
    assert "thread_id" in resp.text


def test_resume_returns_404_when_user_has_no_thread(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.post(
        "/api/chat/resume",
        json={
            "user_id": "u-no-thread",
            "assistant_id": "deepagent_demo",
            "command": {"resume": {"decisions": [{"type": "approve"}]}},
        },
    )
    assert resp.status_code == 404
    assert "No thread" in resp.text


def test_resume_prefers_explicit_thread_id_over_user_mapping(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    first = client.post("/api/thread", json={"user_id": "u-priority-a"})
    second = client.post("/api/thread", json={"user_id": "u-priority-b"})
    assert first.status_code == 200
    assert second.status_code == 200
    explicit_thread_id = second.json()["thread_id"]

    resp = client.post(
        "/api/chat/resume",
        json={
            "user_id": "u-priority-a",
            "thread_id": explicit_thread_id,
            "assistant_id": "deepagent_demo",
            "command": {"resume": {"decisions": [{"type": "approve"}]}},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["thread_id"] == explicit_thread_id


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


def test_assistants_endpoint_returns_raw_semantics(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.get("/api/assistants")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload.get("items"), list)
    assert payload["items"][0]["assistant_id"] == "agent"
    assert payload["items"][0]["graph_id"] == "agent"

    filtered = client.get("/api/assistants", params={"graph_id": "deepagent_demo"})
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["assistant_id"] == "deepagent_demo"


def test_graphs_endpoint_returns_graph_ids(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.get("/api/graphs")
    assert resp.status_code == 200
    payload = resp.json()
    assert "items" in payload
    assert "agent" in payload["items"]


def test_assistant_crud_endpoints(tmp_path: Any, monkeypatch: Any) -> None:
    client, _, _ = _build_test_client(tmp_path, monkeypatch)

    create_resp = client.post(
        "/api/assistants",
        json={
            "graph_id": "agent",
            "name": "Team Helper",
            "context": {"model_provider": "glm4"},
            "config": {"recursion_limit": 40},
            "metadata": {"owner": "qa"},
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()["item"]
    assistant_id = created["assistant_id"]
    assert created["graph_id"] == "agent"
    assert created["name"] == "Team Helper"

    get_resp = client.get(f"/api/assistants/{assistant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["item"]["assistant_id"] == assistant_id

    update_resp = client.patch(
        f"/api/assistants/{assistant_id}",
        json={"name": "Team Helper V2", "graph_id": "deepagent_demo"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()["item"]
    assert updated["name"] == "Team Helper V2"
    assert updated["graph_id"] == "deepagent_demo"

    delete_resp = client.delete(f"/api/assistants/{assistant_id}", params={"delete_threads": "true"})
    assert delete_resp.status_code == 200
    deleted = delete_resp.json()
    assert deleted["assistant_id"] == assistant_id
    assert deleted["deleted"] is True
    assert deleted["delete_threads"] is True


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


def test_wait_recreates_stale_thread(tmp_path: Any, monkeypatch: Any) -> None:
    client, backend, _ = _build_test_client(tmp_path, monkeypatch)

    first = client.post("/api/thread", json={"user_id": "u-stale"})
    assert first.status_code == 200
    stale_thread_id = first.json()["thread_id"]

    backend.messages_by_thread.pop(stale_thread_id, None)

    wait_resp = client.post(
        "/api/chat/wait",
        json={"user_id": "u-stale", "message": "recover", "assistant_id": "agent"},
    )
    assert wait_resp.status_code == 200
    new_thread_id = wait_resp.json()["thread_id"]
    assert new_thread_id != stale_thread_id
    assert new_thread_id in backend.messages_by_thread


def test_wait_context_only_policy_merges_configurable(tmp_path: Any, monkeypatch: Any) -> None:
    client, backend, _ = _build_test_client(tmp_path, monkeypatch)

    resp = client.post(
        "/api/chat/wait",
        json={
            "user_id": "u-context-only",
            "assistant_id": "agent",
            "message": "hello",
            "context": {"system_prompt": "ctx"},
            "config": {"configurable": {"temperature": 0.6, "max_tokens": 256}, "recursion_limit": 60},
        },
    )
    assert resp.status_code == 200
    assert backend.last_wait_context is not None
    assert backend.last_wait_context.get("system_prompt") == "ctx"
    assert backend.last_wait_context.get("temperature") == 0.6
    assert backend.last_wait_context.get("max_tokens") == 256
    assert backend.last_wait_config == {"recursion_limit": 60}


def test_stream_context_only_policy_merges_configurable(tmp_path: Any, monkeypatch: Any) -> None:
    client, backend, _ = _build_test_client(tmp_path, monkeypatch)

    with client.stream(
        "GET",
        "/api/chat/stream",
        params={
            "user_id": "u-context-stream",
            "assistant_id": "agent",
            "message": "ping",
            "context_json": '{"system_prompt":"ctx"}',
            "config_json": '{"configurable":{"temperature":0.5,"top_p":0.9}}',
        },
    ) as resp:
        assert resp.status_code == 200
        _ = "".join(resp.iter_text())

    assert backend.last_stream_context is not None
    assert backend.last_stream_context.get("system_prompt") == "ctx"
    assert backend.last_stream_context.get("temperature") == 0.5
    assert backend.last_stream_context.get("top_p") == 0.9
    assert backend.last_stream_config is None


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
