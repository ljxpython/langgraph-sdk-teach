from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID
from uuid import uuid4

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic import ConfigDict

from src.app.allowlist import is_allowed
from src.app.config import validate_config
from src.app.error_handling import register_error_handling
from src.app.identity import require_identity

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handling(app)

DB_PATH = Path(__file__).resolve().parents[2] / "db.sqlite"
DEFAULT_ASSISTANT_ID = "agent"


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProxyCheckRequest(StrictRequestModel):
    method: str
    path: str


class CreateThreadRequest(StrictRequestModel):
    assistant_id: str = "agent"
    metadata: dict[str, object] | None = None


class SearchThreadsRequest(StrictRequestModel):
    assistant_id: str | None = None
    metadata: dict[str, object] | None = None
    limit: int | None = None
    offset: int | None = None


class RunRequest(StrictRequestModel):
    assistant_id: str | None = None
    message: str | None = None
    input: dict[str, object] | None = None
    config: dict[str, object] | None = None
    context: dict[str, object] | None = None
    metadata: dict[str, object] | None = None
    command: dict[str, object] | None = None
    checkpoint: dict[str, object] | None = None
    checkpoint_id: str | None = None
    checkpoint_during: bool | None = None
    stream_mode: list[str] | str | None = None
    stream_subgraphs: bool | None = None
    stream_resumable: bool | None = None
    feedback_keys: list[str] | None = None
    multitask_strategy: str | None = None
    on_completion: str | None = None
    on_disconnect: str | None = None
    after_seconds: int | float | None = None
    if_not_exists: str | None = None
    webhook: str | None = None
    durability: str | None = None
    interrupt_before: list[str] | None = None
    interrupt_after: list[str] | None = None


class ThreadHistoryRequest(StrictRequestModel):
    limit: int | None = None
    before: dict[str, object] | None = None
    checkpoint: dict[str, object] | None = None
    metadata: dict[str, object] | None = None


def _open_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_session_map_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            assistant_id TEXT NOT NULL,
            platform_session_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tenant_id, user_id, assistant_id)
        )
        """
    )


def _ensure_run_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            platform_session_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            status TEXT NOT NULL,
            latency INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(run_log)").fetchall()}
    if "trace_id" not in columns:
        conn.execute("ALTER TABLE run_log ADD COLUMN trace_id TEXT NOT NULL DEFAULT ''")
    if "latency" not in columns:
        conn.execute("ALTER TABLE run_log ADD COLUMN latency INTEGER NOT NULL DEFAULT 0")


def _ensure_idempotency_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tenant_id, user_id, idempotency_key)
        )
        """
    )


def _build_idempotency_fingerprint(
    assistant_id: str,
    thread_id: str,
    platform_session_id: str,
    created_at: str,
) -> str:
    return (
        f"assistant_id={assistant_id};"
        f"thread_id={thread_id};"
        f"platform_session_id={platform_session_id};"
        f"created_at={created_at}"
    )


def _parse_idempotency_fingerprint(value: str) -> dict[str, str]:
    pairs = [part for part in value.split(";") if part]
    parsed: dict[str, str] = {}
    for pair in pairs:
        key, sep, raw_value = pair.partition("=")
        if sep != "=" or not key or not raw_value:
            continue
        parsed[key] = raw_value
    return parsed


def _fetch_idempotent_thread_by_key(
    conn: sqlite3.Connection,
    tenant_id: str,
    user_id: str,
    idempotency_key: str,
) -> dict[str, object] | None:
    _ensure_idempotency_table(conn)
    row = conn.execute(
        """
        SELECT request_fingerprint
        FROM idempotency
        WHERE tenant_id = ? AND user_id = ? AND idempotency_key = ?
        LIMIT 1
        """,
        (tenant_id, user_id, idempotency_key),
    ).fetchone()
    if row is None:
        return None

    payload = _parse_idempotency_fingerprint(row["request_fingerprint"])
    required = {"assistant_id", "thread_id", "platform_session_id", "created_at"}
    if required.issubset(payload):
        session_row = conn.execute(
            "SELECT thread_id, platform_session_id, created_at FROM session_map WHERE tenant_id = ? AND user_id = ? AND thread_id = ? LIMIT 1",
            (tenant_id, user_id, payload["thread_id"]),
        ).fetchone()
        if session_row is not None:
            return {
                "thread_id": session_row["thread_id"],
                "created_at": session_row["created_at"],
                "metadata": {
                    "assistant_id": payload["assistant_id"],
                    "platform_session_id": session_row["platform_session_id"],
                },
            }
        return {
            "thread_id": payload["thread_id"],
            "created_at": payload["created_at"],
            "metadata": {
                "assistant_id": payload["assistant_id"],
                "platform_session_id": payload["platform_session_id"],
            },
        }

    assistant_id = payload.get("assistant_id")
    if not assistant_id:
        return None

    session_row = conn.execute(
        """
        SELECT tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at
        FROM session_map
        WHERE tenant_id = ? AND user_id = ? AND assistant_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (tenant_id, user_id, assistant_id),
    ).fetchone()
    if session_row is None:
        return None
    return _to_thread_payload(session_row)


def _insert_idempotency_record(
    conn: sqlite3.Connection,
    tenant_id: str,
    user_id: str,
    idempotency_key: str,
    request_fingerprint: str,
) -> None:
    _ensure_idempotency_table(conn)
    conn.execute(
        """
        INSERT INTO idempotency (
            tenant_id,
            user_id,
            idempotency_key,
            request_fingerprint,
            created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (tenant_id, user_id, idempotency_key, request_fingerprint, datetime.now(timezone.utc).isoformat()),
    )


def _get_owned_thread(
    conn: sqlite3.Connection,
    tenant_id: str,
    user_id: str,
    thread_id: str,
) -> sqlite3.Row | None:
    _ensure_session_map_table(conn)
    return conn.execute(
        """
        SELECT tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at
        FROM session_map
        WHERE tenant_id = ? AND user_id = ? AND thread_id = ?
        LIMIT 1
        """,
        (tenant_id, user_id, thread_id),
    ).fetchone()


def _insert_run_log(
    conn: sqlite3.Connection,
    trace_id: str,
    tenant_id: str,
    user_id: str,
    platform_session_id: str,
    thread_id: str,
    run_id: str,
    status: str,
    latency: int,
) -> None:
    _ensure_run_log_table(conn)
    conn.execute(
        """
        INSERT INTO run_log (
            trace_id,
            tenant_id,
            user_id,
            platform_session_id,
            thread_id,
            run_id,
            status,
            latency,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id,
            tenant_id,
            user_id,
            platform_session_id,
            thread_id,
            run_id,
            status,
            latency,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def _resolve_run_log_lookup(platform_session_id: str | None, run_id: str | None) -> tuple[str, str]:
    has_session = bool(platform_session_id)
    has_run = bool(run_id)
    if has_session == has_run:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one query parameter: platform_session_id or run_id",
        )

    lookup_key = "platform_session_id" if has_session else "run_id"
    lookup_value = platform_session_id if has_session else run_id
    assert lookup_value is not None
    try:
        UUID(lookup_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{lookup_key} must be a valid UUID") from exc
    return lookup_key, lookup_value


def _lookup_owned_run_logs(
    conn: sqlite3.Connection,
    tenant_id: str,
    user_id: str,
    platform_session_id: str | None = None,
    run_id: str | None = None,
) -> list[sqlite3.Row]:
    _ensure_run_log_table(conn)
    if platform_session_id is not None:
        return conn.execute(
            """
            SELECT trace_id, tenant_id, user_id, platform_session_id, thread_id, run_id, status, latency, created_at
            FROM run_log
            WHERE tenant_id = ? AND user_id = ? AND platform_session_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (tenant_id, user_id, platform_session_id),
        ).fetchall()

    assert run_id is not None
    return conn.execute(
        """
        SELECT trace_id, tenant_id, user_id, platform_session_id, thread_id, run_id, status, latency, created_at
        FROM run_log
        WHERE tenant_id = ? AND user_id = ? AND run_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (tenant_id, user_id, run_id),
    ).fetchall()


def _get_latest_owned_run(
    conn: sqlite3.Connection,
    tenant_id: str,
    user_id: str,
    thread_id: str,
) -> sqlite3.Row | None:
    _ensure_run_log_table(conn)
    return conn.execute(
        """
        SELECT tenant_id, user_id, platform_session_id, thread_id, run_id, status, created_at
        FROM run_log
        WHERE tenant_id = ? AND user_id = ? AND thread_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (tenant_id, user_id, thread_id),
    ).fetchone()


def _to_thread_payload(row: sqlite3.Row) -> dict[str, object]:
    return {
        "thread_id": row["thread_id"],
        "created_at": row["created_at"],
        "metadata": {
            "assistant_id": row["assistant_id"],
            "platform_session_id": row["platform_session_id"],
        },
    }


def _to_history_payload(row: sqlite3.Row, *, previous_checkpoint_id: str | None = None) -> dict[str, object]:
    checkpoint_id = row["run_id"]
    checkpoint = {
        "thread_id": row["thread_id"],
        "checkpoint_ns": "",
        "checkpoint_id": checkpoint_id,
        "checkpoint_map": None,
    }
    parent_checkpoint = (
        {
            "thread_id": row["thread_id"],
            "checkpoint_ns": "",
            "checkpoint_id": previous_checkpoint_id,
            "checkpoint_map": None,
        }
        if previous_checkpoint_id
        else None
    )
    return {
        "values": {"messages": []},
        "next": [],
        "checkpoint": checkpoint,
        "metadata": {
            "source": "loop",
            "writes": {"status": row["status"]},
        },
        "created_at": row["created_at"],
        "parent_checkpoint": parent_checkpoint,
        "tasks": [
            {
                "id": row["run_id"],
                "name": "run",
                "result": None,
                "error": None,
                "interrupts": [],
                "checkpoint": None,
                "state": None,
            }
        ],
    }


def _assistant_payload(assistant_id: str) -> dict[str, str]:
    return {
        "assistant_id": assistant_id,
        "name": assistant_id,
    }


@app.on_event("startup")
async def startup_validate_config() -> None:
    validate_config()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "platform_core",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info")
def info() -> dict[str, str]:
    return {
        "service": "platform_core",
        "status": "ok",
    }


@app.get("/whoami")
def whoami(request: Request, _: tuple[str, str] = Depends(require_identity)) -> dict[str, str]:
    return {
        "tenant_id": request.state.tenant_id,
        "user_id": request.state.user_id,
    }


@app.post("/assistants/search")
def search_assistants(_: tuple[str, str] = Depends(require_identity)) -> list[dict[str, str]]:
    return [_assistant_payload(DEFAULT_ASSISTANT_ID)]


@app.get("/assistants/{assistant_id}")
def get_assistant(assistant_id: str, _: tuple[str, str] = Depends(require_identity)) -> dict[str, str]:
    if assistant_id != DEFAULT_ASSISTANT_ID:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return _assistant_payload(DEFAULT_ASSISTANT_ID)


@app.post("/proxy/check")
def proxy_check(payload: ProxyCheckRequest) -> dict[str, str | bool]:
    if not is_allowed(payload.method, payload.path):
        raise HTTPException(status_code=403, detail="Endpoint not allowed")
    return {
        "allowed": True,
        "method": payload.method,
        "path": payload.path,
    }


@app.post("/threads")
def create_thread(
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    payload: CreateThreadRequest | None = None,
) -> dict[str, object]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    assistant_id = payload.assistant_id if payload and payload.assistant_id else "agent"
    idempotency_key = request.headers.get("Idempotency-Key")

    with _open_db() as conn:
        _ensure_session_map_table(conn)
        _ensure_idempotency_table(conn)

        if idempotency_key:
            existing_payload = _fetch_idempotent_thread_by_key(conn, tenant_id, user_id, idempotency_key)
            if existing_payload is not None:
                return existing_payload

            thread_id = str(uuid4())
            platform_session_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            response_payload = {
                "thread_id": thread_id,
                "created_at": created_at,
                "metadata": {
                    "assistant_id": assistant_id,
                    "platform_session_id": platform_session_id,
                },
            }

            request_fingerprint = _build_idempotency_fingerprint(
                assistant_id=assistant_id,
                thread_id=thread_id,
                platform_session_id=platform_session_id,
                created_at=created_at,
            )
            try:
                _insert_idempotency_record(
                    conn,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                )
            except sqlite3.IntegrityError:
                existing_payload = _fetch_idempotent_thread_by_key(conn, tenant_id, user_id, idempotency_key)
                if existing_payload is not None:
                    return existing_payload
                raise

            try:
                conn.execute(
                    """
                    INSERT INTO session_map (
                        tenant_id,
                        user_id,
                        assistant_id,
                        platform_session_id,
                        thread_id,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at),
                )
            except sqlite3.IntegrityError:
                conn.execute(
                    """
                    UPDATE session_map
                    SET platform_session_id = ?, thread_id = ?, created_at = ?
                    WHERE tenant_id = ? AND user_id = ? AND assistant_id = ?
                    """,
                    (platform_session_id, thread_id, created_at, tenant_id, user_id, assistant_id),
                )
            return response_payload

        thread_id = str(uuid4())
        platform_session_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                """
                INSERT INTO session_map (
                    tenant_id,
                    user_id,
                    assistant_id,
                    platform_session_id,
                    thread_id,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at),
            )
        except sqlite3.IntegrityError:
            conn.execute(
                """
                UPDATE session_map
                SET platform_session_id = ?, thread_id = ?, created_at = ?
                WHERE tenant_id = ? AND user_id = ? AND assistant_id = ?
                """,
                (platform_session_id, thread_id, created_at, tenant_id, user_id, assistant_id),
            )

    return {
        "thread_id": thread_id,
        "created_at": created_at,
        "metadata": {
            "assistant_id": assistant_id,
            "platform_session_id": platform_session_id,
        },
    }


@app.post("/threads/search")
def search_threads(
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    payload: SearchThreadsRequest | None = None,
) -> list[dict[str, object]]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    assistant_id = payload.assistant_id if payload and payload.assistant_id else None
    if assistant_id is None and payload and payload.metadata:
        raw_assistant_id = payload.metadata.get("assistant_id")
        raw_graph_id = payload.metadata.get("graph_id")
        if isinstance(raw_assistant_id, str) and raw_assistant_id.strip():
            assistant_id = raw_assistant_id.strip()
        elif isinstance(raw_graph_id, str) and raw_graph_id.strip():
            assistant_id = raw_graph_id.strip()
    limit = payload.limit if payload and payload.limit and payload.limit > 0 else None
    offset = payload.offset if payload and payload.offset and payload.offset > 0 else 0

    with _open_db() as conn:
        _ensure_session_map_table(conn)
        if assistant_id:
            rows = conn.execute(
                """
                SELECT tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at
                FROM session_map
                WHERE tenant_id = ? AND user_id = ? AND assistant_id = ?
                ORDER BY created_at DESC
                """,
                (tenant_id, user_id, assistant_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at
                FROM session_map
                WHERE tenant_id = ? AND user_id = ?
                ORDER BY created_at DESC
                """,
                (tenant_id, user_id),
            ).fetchall()

    rows = rows[offset:]
    if limit is not None:
        rows = rows[:limit]

    return [_to_thread_payload(row) for row in rows]


@app.get("/threads/{thread_id}")
def get_thread(
    thread_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
) -> dict[str, object]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id

    with _open_db() as conn:
        _ensure_session_map_table(conn)
        row = conn.execute(
            """
            SELECT tenant_id, user_id, assistant_id, platform_session_id, thread_id, created_at
            FROM session_map
            WHERE tenant_id = ? AND user_id = ? AND thread_id = ?
            LIMIT 1
            """,
            (tenant_id, user_id, thread_id),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    return _to_thread_payload(row)


@app.get("/threads/{thread_id}/state")
def get_thread_state(
    thread_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
) -> dict[str, str | None]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id

    with _open_db() as conn:
        thread_row = _get_owned_thread(conn, tenant_id, user_id, thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        run_row = _get_latest_owned_run(conn, tenant_id, user_id, thread_id)

    updated_at = run_row["created_at"] if run_row is not None else thread_row["created_at"]
    latest_run_status = run_row["status"] if run_row is not None else None

    return {
        "thread_id": thread_id,
        "latest_run_status": latest_run_status,
        "updated_at": updated_at,
    }


@app.post("/threads/{thread_id}/history")
def get_thread_history(
    thread_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    payload: ThreadHistoryRequest | None = None,
) -> list[dict[str, object]]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    limit = payload.limit if payload and payload.limit and payload.limit > 0 else 10

    with _open_db() as conn:
        thread_row = _get_owned_thread(conn, tenant_id, user_id, thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        _ensure_run_log_table(conn)
        rows = conn.execute(
            """
            SELECT tenant_id, user_id, platform_session_id, thread_id, run_id, status, created_at
            FROM run_log
            WHERE tenant_id = ? AND user_id = ? AND thread_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (tenant_id, user_id, thread_id, limit),
        ).fetchall()

    if not rows:
        return [
            {
                "values": {"messages": []},
                "next": [],
                "checkpoint": {
                    "thread_id": thread_id,
                    "checkpoint_ns": "",
                    "checkpoint_id": thread_row["platform_session_id"],
                    "checkpoint_map": None,
                },
                "metadata": {
                    "source": "input",
                    "writes": {},
                },
                "created_at": thread_row["created_at"],
                "parent_checkpoint": None,
                "tasks": [],
            }
        ]

    history: list[dict[str, object]] = []
    previous_checkpoint_id: str | None = None
    for row in rows:
        history.append(_to_history_payload(row, previous_checkpoint_id=previous_checkpoint_id))
        previous_checkpoint_id = row["run_id"]
    return history


@app.post("/threads/{thread_id}/runs/wait")
def create_run_wait(
    thread_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    payload: RunRequest | None = None,
) -> dict[str, str]:
    del payload
    started_at = perf_counter()
    trace_id = request.state.trace_id
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    run_id = str(uuid4())
    status = "completed"

    with _open_db() as conn:
        thread_row = _get_owned_thread(conn, tenant_id, user_id, thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        latency = int((perf_counter() - started_at) * 1000)
        _insert_run_log(
            conn,
            trace_id,
            tenant_id,
            user_id,
            thread_row["platform_session_id"],
            thread_id,
            run_id,
            status,
            latency,
        )

    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "status": status,
        "trace_id": trace_id,
    }


@app.post("/threads/{thread_id}/runs/stream")
def create_run_stream(
    thread_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    payload: RunRequest | None = None,
) -> StreamingResponse:
    del payload
    started_at = perf_counter()
    trace_id = request.state.trace_id
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    run_id = str(uuid4())
    status = "completed"

    with _open_db() as conn:
        thread_row = _get_owned_thread(conn, tenant_id, user_id, thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        latency = int((perf_counter() - started_at) * 1000)
        _insert_run_log(
            conn,
            trace_id,
            tenant_id,
            user_id,
            thread_row["platform_session_id"],
            thread_id,
            run_id,
            status,
            latency,
        )

    def event_stream() -> Iterator[str]:
        metadata_payload = json.dumps(
            {
                "run_id": run_id,
                "thread_id": thread_id,
                "status": status,
                "trace_id": trace_id,
            }
        )
        done_payload = json.dumps(
            {
                "run_id": run_id,
                "thread_id": thread_id,
                "status": status,
            }
        )
        yield f"event: metadata\ndata: {metadata_payload}\n\n"
        yield f"event: done\ndata: {done_payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/run-logs")
def get_run_logs(
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
    platform_session_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, list[dict[str, object]]]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id
    lookup_key, lookup_value = _resolve_run_log_lookup(platform_session_id=platform_session_id, run_id=run_id)

    with _open_db() as conn:
        if lookup_key == "platform_session_id":
            rows = _lookup_owned_run_logs(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                platform_session_id=lookup_value,
            )
        else:
            rows = _lookup_owned_run_logs(
                conn,
                tenant_id=tenant_id,
                user_id=user_id,
                run_id=lookup_value,
            )

    return {
        "run_logs": [
            {
                "trace_id": row["trace_id"],
                "tenant_id": row["tenant_id"],
                "user_id": row["user_id"],
                "platform_session_id": row["platform_session_id"],
                "thread_id": row["thread_id"],
                "run_id": row["run_id"],
                "status": row["status"],
                "latency": row["latency"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/threads/{thread_id}/runs/{run_id}/join")
def join_run(
    thread_id: str,
    run_id: str,
    request: Request,
    _: tuple[str, str] = Depends(require_identity),
) -> dict[str, str]:
    tenant_id = request.state.tenant_id
    user_id = request.state.user_id

    with _open_db() as conn:
        thread_row = _get_owned_thread(conn, tenant_id, user_id, thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        _ensure_run_log_table(conn)
        run_row = conn.execute(
            """
            SELECT tenant_id, user_id, platform_session_id, thread_id, run_id, status, created_at
            FROM run_log
            WHERE tenant_id = ? AND user_id = ? AND thread_id = ? AND run_id = ?
            LIMIT 1
            """,
            (tenant_id, user_id, thread_id, run_id),
        ).fetchone()

    if run_row is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "run_id": run_row["run_id"],
        "thread_id": run_row["thread_id"],
        "status": run_row["status"],
        "created_at": run_row["created_at"],
    }
