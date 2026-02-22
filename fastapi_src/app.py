from __future__ import annotations

import time
import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from fastapi_src.api.routes import create_router
from fastapi_src.core.config import get_settings
from fastapi_src.core.logging import get_logger, setup_logging
from fastapi_src.db.sqlite import init_db
from fastapi_src.repositories.run_log_repo import RunLogRepository
from fastapi_src.repositories.thread_repo import ThreadRepository
from fastapi_src.services.chat_service import ChatService


settings = get_settings()
setup_logging()
logger = get_logger(__name__)
thread_repo = ThreadRepository(settings.sqlite_path)
run_log_repo = RunLogRepository(settings.sqlite_path)
chat_service = ChatService(thread_repo, settings, run_log_repo=run_log_repo)

app = FastAPI(title="LangGraph Service Core API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(create_router(chat_service))


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    started = time.perf_counter()
    logger.info("request.started id=%s method=%s path=%s", request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.exception("request.failed id=%s path=%s elapsed_ms=%s", request_id, request.url.path, elapsed_ms)
        raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request.completed id=%s method=%s path=%s status=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.on_event("startup")
async def startup_init() -> None:
    init_db(settings.sqlite_path)
    logger.info(
        "startup.ready sqlite_path=%s langgraph_api_url=%s cors_origins=%s",
        settings.sqlite_path,
        settings.langgraph_api_url,
        settings.cors_origins,
    )
