from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph_sdk import get_client
from pydantic import BaseModel, Field


app = FastAPI(title="LangGraph Observer Learning API")
_thread_by_user: dict[str, str] = {}


def _client(api_url: str):
    return get_client(url=api_url)


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


class ThreadRequest(BaseModel):
    user_id: str = Field(min_length=1)
    api_url: str = "http://127.0.0.1:8123"


class WaitRunRequest(BaseModel):
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    assistant_id: str = "agent"
    api_url: str = "http://127.0.0.1:8123"
    context: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


@app.post("/api/thread")
async def create_or_get_thread(req: ThreadRequest) -> JSONResponse:
    if req.user_id in _thread_by_user:
        return JSONResponse({"user_id": req.user_id, "thread_id": _thread_by_user[req.user_id], "created": False})

    thread = await _client(req.api_url).threads.create()
    thread_id = thread["thread_id"]
    _thread_by_user[req.user_id] = thread_id
    return JSONResponse({"user_id": req.user_id, "thread_id": thread_id, "created": True})


@app.post("/api/chat/wait")
async def chat_wait(req: WaitRunRequest) -> JSONResponse:
    if req.user_id not in _thread_by_user:
        thread = await _client(req.api_url).threads.create()
        _thread_by_user[req.user_id] = thread["thread_id"]

    thread_id = _thread_by_user[req.user_id]
    result = await _client(req.api_url).runs.wait(
        thread_id,
        req.assistant_id,
        input={"messages": [{"role": "human", "content": req.message}]},
        context=req.context,
        config=req.config,
    )
    return JSONResponse({"thread_id": thread_id, "result": result})


@app.get("/api/chat/stream")
async def chat_stream(
    user_id: str,
    message: str,
    assistant_id: str = "agent",
    api_url: str = "http://127.0.0.1:8123",
    stream_mode: str = "messages,updates,tasks,checkpoints,debug",
    context_json: str | None = Query(default=None),
    config_json: str | None = Query(default=None),
) -> StreamingResponse:
    if user_id not in _thread_by_user:
        thread = await _client(api_url).threads.create()
        _thread_by_user[user_id] = thread["thread_id"]

    context = json.loads(context_json) if context_json else None
    config = json.loads(config_json) if config_json else None
    modes = [x.strip() for x in stream_mode.split(",") if x.strip()]
    thread_id = _thread_by_user[user_id]

    async def event_gen() -> AsyncIterator[str]:
        yield _sse("meta", {"thread_id": thread_id, "assistant_id": assistant_id})
        try:
            async for chunk in _client(api_url).runs.stream(
                thread_id,
                assistant_id,
                input={"messages": [{"role": "human", "content": message}]},
                context=context,
                config=config,
                stream_mode=modes,
            ):
                yield _sse(chunk.event, chunk.data)
            yield _sse("done", {"ok": True})
        except Exception as exc:
            yield _sse("error", {"error": str(exc)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/state")
async def get_state(user_id: str, api_url: str = "http://127.0.0.1:8123") -> JSONResponse:
    thread_id = _thread_by_user.get(user_id)
    if not thread_id:
        raise HTTPException(status_code=404, detail=f"No thread for user_id={user_id}")
    state = await _client(api_url).threads.get_state(thread_id)
    return JSONResponse({"thread_id": thread_id, "state": state})
