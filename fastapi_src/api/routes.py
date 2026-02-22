from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from fastapi_src.core.langgraph_client import get_langgraph_client
from fastapi_src.core.logging import get_logger
from fastapi_src.models.schemas import ResumeChatRequest, ThreadRequest, WaitChatRequest
from fastapi_src.services.chat_service import ChatService
from fastapi_src.services.sse_service import to_sse_event


def create_router(chat_service: ChatService) -> APIRouter:
    router = APIRouter(prefix="/api")
    logger = get_logger(__name__)

    @router.post("/thread")
    async def create_or_get_thread(req: ThreadRequest) -> dict[str, object]:
        logger.info("api.thread user_id=%s", req.user_id)
        thread_id, created = await chat_service.create_or_get_thread(req.user_id, req.api_url)
        logger.info("api.thread.result user_id=%s thread_id=%s created=%s", req.user_id, thread_id, created)
        return {"user_id": req.user_id, "thread_id": thread_id, "created": created}

    @router.post("/chat/wait")
    async def chat_wait(req: WaitChatRequest) -> dict[str, object]:
        logger.info("api.wait user_id=%s assistant_id=%s", req.user_id, req.assistant_id)
        return await chat_service.wait_chat(
            user_id=req.user_id,
            message=req.message,
            assistant_id=req.assistant_id,
            api_url=req.api_url,
            context=req.context,
            config=req.config,
        )

    @router.post("/chat/resume")
    async def chat_resume(req: ResumeChatRequest) -> dict[str, object]:
        logger.info("api.resume user_id=%s assistant_id=%s", req.user_id, req.assistant_id)
        return await chat_service.resume_chat(
            user_id=req.user_id,
            command=req.command,
            assistant_id=req.assistant_id,
            api_url=req.api_url,
        )

    @router.get("/chat/stream")
    async def chat_stream(
        user_id: str,
        message: str,
        assistant_id: str | None = None,
        api_url: str | None = None,
        stream_mode: str | None = None,
        context_json: str | None = Query(default=None),
        config_json: str | None = Query(default=None),
    ) -> StreamingResponse:
        logger.info("api.stream.start user_id=%s assistant_id=%s", user_id, assistant_id)
        api = chat_service.resolve_api_url(api_url)
        assistant = chat_service.resolve_assistant_id(assistant_id)
        thread_id = await chat_service.ensure_thread(user_id, api)
        context = chat_service.parse_optional_json(context_json, "context_json")
        config = chat_service.parse_optional_json(config_json, "config_json")
        modes = chat_service.parse_stream_mode(stream_mode)

        async def event_gen() -> AsyncIterator[str]:
            try:
                client = get_langgraph_client(api)
                stream_kwargs: dict[str, Any] = {
                    "input": {"messages": [{"role": "human", "content": message}]},
                    "stream_mode": modes,
                }
                if context is not None:
                    stream_kwargs["context"] = context
                if config is not None:
                    stream_kwargs["config"] = config

                stream_fn = cast(Any, client.runs.stream)
                async for chunk in stream_fn(thread_id, assistant, **stream_kwargs):
                    logger.debug("api.stream.chunk user_id=%s thread_id=%s event=%s", user_id, thread_id, str(chunk.event))
                    chat_service.log_stream_chunk(
                        user_id=user_id,
                        thread_id=thread_id,
                        event=str(chunk.event),
                        data=chunk.data,
                    )
                    yield to_sse_event(str(chunk.event), chunk.data)
                chat_service.log_stream_done(user_id=user_id, thread_id=thread_id)
                logger.info("api.stream.done user_id=%s thread_id=%s", user_id, thread_id)
                yield to_sse_event("done", {"ok": True, "thread_id": thread_id})
            except Exception as exc:
                chat_service.log_stream_error(user_id=user_id, thread_id=thread_id, error=str(exc))
                logger.exception("api.stream.error user_id=%s thread_id=%s", user_id, thread_id)
                yield to_sse_event("error", {"error": str(exc), "thread_id": thread_id})

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @router.get("/state")
    async def get_state(user_id: str, api_url: str | None = None) -> dict[str, object]:
        logger.info("api.state user_id=%s", user_id)
        return await chat_service.get_state(user_id=user_id, api_url=api_url)

    @router.get("/run-logs")
    async def get_run_logs(user_id: str) -> dict[str, object]:
        logger.info("api.run_logs user_id=%s", user_id)
        return chat_service.get_run_logs(user_id)

    return router
