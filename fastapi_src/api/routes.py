from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from fastapi_src.core.langgraph_client import get_langgraph_client
from fastapi_src.core.logging import get_logger
from fastapi_src.models.schemas import (
    AssistantCreateRequest,
    ThreadCreateRequest,
    AssistantUpdateRequest,
    ResumeChatRequest,
    ThreadRequest,
    WaitChatRequest,
)
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

    @router.post("/thread/new")
    async def create_thread(req: ThreadCreateRequest) -> dict[str, object]:
        logger.info("api.thread.new user_id=%s", req.user_id)
        return await chat_service.create_thread(api_url=req.api_url, user_id=req.user_id, metadata=req.metadata)

    @router.post("/chat/wait")
    async def chat_wait(req: WaitChatRequest) -> dict[str, object]:
        logger.info("api.wait user_id=%s thread_id=%s assistant_id=%s", req.user_id, req.thread_id, req.assistant_id)
        return await chat_service.wait_chat(
            user_id=req.user_id,
            thread_id=req.thread_id,
            message=req.message,
            assistant_id=req.assistant_id,
            api_url=req.api_url,
            context=req.context,
            config=req.config,
        )

    @router.post("/chat/resume")
    async def chat_resume(req: ResumeChatRequest) -> dict[str, object]:
        logger.info("api.resume user_id=%s thread_id=%s assistant_id=%s", req.user_id, req.thread_id, req.assistant_id)
        return await chat_service.resume_chat(
            user_id=req.user_id,
            thread_id=req.thread_id,
            command=req.command,
            assistant_id=req.assistant_id,
            api_url=req.api_url,
        )

    @router.get("/chat/stream")
    async def chat_stream(
        user_id: str,
        message: str,
        thread_id: str | None = None,
        assistant_id: str | None = None,
        api_url: str | None = None,
        stream_mode: str | None = None,
        context_json: str | None = Query(default=None),
        config_json: str | None = Query(default=None),
    ) -> StreamingResponse:
        logger.info("api.stream.start user_id=%s thread_id=%s assistant_id=%s", user_id, thread_id, assistant_id)
        api = chat_service.resolve_api_url(api_url)
        assistant = chat_service.resolve_assistant_id(assistant_id)
        resolved_thread_id = await chat_service.ensure_thread_ref(user_id=user_id, thread_id=thread_id, api_url=api)
        context = chat_service.parse_optional_json(context_json, "context_json")
        config = chat_service.parse_optional_json(config_json, "config_json")
        context, config = chat_service.normalize_context_and_config(context, config)
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
                async for chunk in stream_fn(resolved_thread_id, assistant, **stream_kwargs):
                    logger.debug("api.stream.chunk user_id=%s thread_id=%s event=%s", user_id, resolved_thread_id, str(chunk.event))
                    chat_service.log_stream_chunk(
                        user_id=user_id,
                        thread_id=resolved_thread_id,
                        event=str(chunk.event),
                        data=chunk.data,
                    )
                    yield to_sse_event(str(chunk.event), chunk.data)
                chat_service.log_stream_done(user_id=user_id, thread_id=resolved_thread_id)
                logger.info("api.stream.done user_id=%s thread_id=%s", user_id, resolved_thread_id)
                yield to_sse_event("done", {"ok": True, "thread_id": resolved_thread_id})
            except Exception as exc:
                chat_service.log_stream_error(user_id=user_id, thread_id=resolved_thread_id, error=str(exc))
                logger.exception("api.stream.error user_id=%s thread_id=%s", user_id, resolved_thread_id)
                yield to_sse_event("error", {"error": str(exc), "thread_id": resolved_thread_id})

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @router.get("/state")
    async def get_state(user_id: str | None = None, thread_id: str | None = None, api_url: str | None = None) -> dict[str, object]:
        logger.info("api.state user_id=%s thread_id=%s", user_id, thread_id)
        return await chat_service.get_state(user_id=user_id, thread_id=thread_id, api_url=api_url)

    @router.get("/messages")
    async def get_messages(
        user_id: str | None = None,
        thread_id: str | None = None,
        api_url: str | None = None,
        limit: int = Query(default=200, ge=1, le=2000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        logger.info("api.messages user_id=%s thread_id=%s limit=%s offset=%s", user_id, thread_id, limit, offset)
        return await chat_service.get_messages(user_id=user_id, thread_id=thread_id, api_url=api_url, limit=limit, offset=offset)

    @router.get("/history")
    async def get_history(
        user_id: str | None = None,
        thread_id: str | None = None,
        api_url: str | None = None,
        limit: int = Query(default=20, ge=1, le=200),
    ) -> dict[str, object]:
        logger.info("api.history user_id=%s thread_id=%s limit=%s", user_id, thread_id, limit)
        return await chat_service.get_history(user_id=user_id, thread_id=thread_id, api_url=api_url, limit=limit)

    @router.get("/run-logs")
    async def get_run_logs(user_id: str | None = None, thread_id: str | None = None) -> dict[str, object]:
        logger.info("api.run_logs user_id=%s thread_id=%s", user_id, thread_id)
        return chat_service.get_run_logs(user_id=user_id, thread_id=thread_id)

    @router.get("/threads")
    async def get_threads(
        api_url: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        logger.info("api.threads limit=%s offset=%s", limit, offset)
        return await chat_service.list_threads(api_url=api_url, limit=limit, offset=offset)

    @router.get("/assistants")
    async def get_assistants(
        api_url: str | None = None,
        graph_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        logger.info("api.assistants graph_id=%s limit=%s offset=%s", graph_id, limit, offset)
        return await chat_service.list_assistants(
            api_url=api_url,
            graph_id=graph_id,
            limit=limit,
            offset=offset,
        )

    @router.get("/graphs")
    async def get_graphs(api_url: str | None = None) -> dict[str, list[str]]:
        logger.info("api.graphs")
        return await chat_service.list_graph_ids(api_url=api_url)

    @router.get("/assistants/{assistant_id}")
    async def get_assistant(assistant_id: str, api_url: str | None = None) -> dict[str, object]:
        logger.info("api.assistant.get assistant_id=%s", assistant_id)
        return await chat_service.get_assistant(assistant_id=assistant_id, api_url=api_url)

    @router.post("/assistants")
    async def create_assistant(req: AssistantCreateRequest) -> dict[str, object]:
        logger.info("api.assistant.create graph_id=%s", req.graph_id)
        return await chat_service.create_assistant(
            graph_id=req.graph_id,
            name=req.name,
            description=req.description,
            config=req.config,
            context=req.context,
            metadata=req.metadata,
            api_url=req.api_url,
        )

    @router.patch("/assistants/{assistant_id}")
    async def update_assistant(assistant_id: str, req: AssistantUpdateRequest) -> dict[str, object]:
        logger.info("api.assistant.update assistant_id=%s", assistant_id)
        return await chat_service.update_assistant(
            assistant_id=assistant_id,
            graph_id=req.graph_id,
            name=req.name,
            description=req.description,
            config=req.config,
            context=req.context,
            metadata=req.metadata,
            api_url=req.api_url,
        )

    @router.delete("/assistants/{assistant_id}")
    async def delete_assistant(
        assistant_id: str,
        delete_threads: bool = Query(default=False),
        api_url: str | None = None,
    ) -> dict[str, object]:
        logger.info("api.assistant.delete assistant_id=%s delete_threads=%s", assistant_id, delete_threads)
        return await chat_service.delete_assistant(
            assistant_id=assistant_id,
            api_url=api_url,
            delete_threads=delete_threads,
        )

    return router
