from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

TRACE_HEADER_NAME = "X-Trace-Id"


def _ensure_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if isinstance(trace_id, str) and trace_id:
        return trace_id
    trace_id = str(uuid4())
    request.state.trace_id = trace_id
    return trace_id


def _error_payload(code: str, message: str, trace_id: str) -> dict[str, str]:
    return {"code": code, "message": message, "trace_id": trace_id}


def register_error_handling(app: FastAPI) -> None:
    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers[TRACE_HEADER_NAME] = trace_id
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        trace_id = _ensure_trace_id(request)
        message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code="http_error", message=message, trace_id=trace_id),
            headers={TRACE_HEADER_NAME: trace_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        trace_id = _ensure_trace_id(request)
        message = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(code="http_error", message=message, trace_id=trace_id),
            headers={TRACE_HEADER_NAME: trace_id},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        trace_id = _ensure_trace_id(request)
        return JSONResponse(
            status_code=400,
            content=_error_payload(code="http_error", message=str(exc), trace_id=trace_id),
            headers={TRACE_HEADER_NAME: trace_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = _ensure_trace_id(request)
        _ = exc
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                code="internal_error",
                message="Internal Server Error",
                trace_id=trace_id,
            ),
            headers={TRACE_HEADER_NAME: trace_id},
        )
