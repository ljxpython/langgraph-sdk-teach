from __future__ import annotations

import json
from typing import Any, cast

from fastapi import HTTPException

from fastapi_src.core.config import Settings
from fastapi_src.core.langgraph_client import get_langgraph_client
from fastapi_src.core.logging import get_logger
from fastapi_src.repositories.thread_repo import ThreadRepository
from fastapi_src.repositories.run_log_repo import RunLogRepository


class ChatService:
    def __init__(self, repo: ThreadRepository, settings: Settings, run_log_repo: RunLogRepository | None = None) -> None:
        self._repo = repo
        self._settings = settings
        self._run_log_repo = run_log_repo
        self._logger = get_logger(__name__)

    def resolve_api_url(self, api_url: str | None) -> str:
        return api_url if api_url else self._settings.langgraph_api_url

    def resolve_assistant_id(self, assistant_id: str | None) -> str:
        return assistant_id if assistant_id else self._settings.default_assistant_id

    def parse_optional_json(self, raw: str | None, field_name: str) -> dict[str, Any] | None:
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._logger.warning("chat.parse_json.invalid field=%s", field_name)
            raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON") from exc
        if not isinstance(value, dict):
            self._logger.warning("chat.parse_json.not_object field=%s", field_name)
            raise HTTPException(status_code=400, detail=f"{field_name} 必须是 JSON 对象")
        return value

    def parse_stream_mode(self, raw: str | None) -> list[str]:
        value = raw if raw else self._settings.default_stream_mode
        modes = [x.strip() for x in value.split(",") if x.strip()]
        return modes if modes else ["messages", "updates", "tasks", "checkpoints", "debug"]

    async def create_or_get_thread(self, user_id: str, api_url: str | None) -> tuple[str, bool]:
        existing = self._repo.get_thread_id(user_id)
        if existing:
            self._logger.info("chat.thread.reuse user_id=%s thread_id=%s", user_id, existing)
            return existing, False

        client = get_langgraph_client(self.resolve_api_url(api_url))
        created = await client.threads.create()
        thread_id = str(created["thread_id"])
        self._repo.upsert_thread_id(user_id, thread_id)
        self._logger.info("chat.thread.create user_id=%s thread_id=%s", user_id, thread_id)
        return thread_id, True

    async def ensure_thread(self, user_id: str, api_url: str | None) -> str:
        thread_id, _ = await self.create_or_get_thread(user_id, api_url)
        return thread_id

    async def wait_chat(
        self,
        user_id: str,
        message: str,
        assistant_id: str | None,
        api_url: str | None,
        context: dict[str, Any] | None,
        config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        assistant = self.resolve_assistant_id(assistant_id)
        thread_id = await self.ensure_thread(user_id, api)
        client = get_langgraph_client(api)
        run_kwargs: dict[str, Any] = {
            "input": {"messages": [{"role": "human", "content": message}]},
        }
        if context is not None:
            run_kwargs["context"] = context
        if config is not None:
            run_kwargs["config"] = config
        self._logger.info("chat.wait.start user_id=%s thread_id=%s assistant_id=%s", user_id, thread_id, assistant)
        result = await client.runs.wait(thread_id, assistant, **run_kwargs)
        self.log_run_result(
            user_id=user_id,
            thread_id=thread_id,
            result=result,
            endpoint="/api/chat/wait",
            event="wait",
        )
        self._logger.info("chat.wait.done user_id=%s thread_id=%s", user_id, thread_id)
        return {"thread_id": thread_id, "result": result}

    async def resume_chat(
        self,
        user_id: str,
        command: dict[str, Any],
        assistant_id: str | None,
        api_url: str | None,
    ) -> dict[str, Any]:
        thread_id = self._repo.get_thread_id(user_id)
        if not thread_id:
            self._logger.warning("chat.resume.missing_thread user_id=%s", user_id)
            raise HTTPException(status_code=404, detail=f"No thread for user_id={user_id}")

        api = self.resolve_api_url(api_url)
        assistant = self.resolve_assistant_id(assistant_id)
        client = get_langgraph_client(api)
        self._logger.info("chat.resume.start user_id=%s thread_id=%s assistant_id=%s", user_id, thread_id, assistant)
        wait_fn = cast(Any, client.runs.wait)
        result = await wait_fn(thread_id, assistant, input=None, command=command)
        self.log_run_result(
            user_id=user_id,
            thread_id=thread_id,
            result=result,
            endpoint="/api/chat/resume",
            event="resume",
        )
        self._logger.info("chat.resume.done user_id=%s thread_id=%s", user_id, thread_id)
        return {"thread_id": thread_id, "result": result}

    async def get_state(self, user_id: str, api_url: str | None) -> dict[str, Any]:
        thread_id = self._repo.get_thread_id(user_id)
        if not thread_id:
            self._logger.warning("chat.state.missing_thread user_id=%s", user_id)
            raise HTTPException(status_code=404, detail=f"No thread for user_id={user_id}")
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        state = await client.threads.get_state(thread_id)
        self._logger.info("chat.state.done user_id=%s thread_id=%s", user_id, thread_id)
        return {"thread_id": thread_id, "state": state}

    def get_run_logs(self, user_id: str) -> dict[str, Any]:
        if self._run_log_repo is None:
            return {"user_id": user_id, "items": []}
        items = self._run_log_repo.list_by_user(user_id)
        self._logger.info("chat.run_logs user_id=%s count=%s", user_id, len(items))
        return {"user_id": user_id, "items": items}

    def log_run_result(
        self,
        *,
        user_id: str,
        thread_id: str,
        result: Any,
        endpoint: str,
        event: str,
    ) -> None:
        if self._run_log_repo is None:
            return
        run_id = self.extract_run_id(result)
        self._run_log_repo.append(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            endpoint=endpoint,
            event=event,
            status="success",
        )
        self._logger.debug(
            "chat.log.run user_id=%s thread_id=%s endpoint=%s event=%s run_id=%s",
            user_id,
            thread_id,
            endpoint,
            event,
            run_id,
        )

    def log_stream_chunk(self, *, user_id: str, thread_id: str, event: str, data: Any) -> None:
        if self._run_log_repo is None:
            return
        run_id = self.extract_run_id(data)
        self._run_log_repo.append(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            endpoint="/api/chat/stream",
            event=event,
            status="streaming",
        )
        self._logger.debug("chat.log.stream user_id=%s thread_id=%s event=%s", user_id, thread_id, event)

    def log_stream_done(self, *, user_id: str, thread_id: str) -> None:
        if self._run_log_repo is None:
            return
        self._run_log_repo.append(
            user_id=user_id,
            thread_id=thread_id,
            run_id=None,
            endpoint="/api/chat/stream",
            event="done",
            status="done",
        )
        self._logger.info("chat.log.stream.done user_id=%s thread_id=%s", user_id, thread_id)

    def log_stream_error(self, *, user_id: str, thread_id: str, error: str) -> None:
        if self._run_log_repo is None:
            return
        self._run_log_repo.append(
            user_id=user_id,
            thread_id=thread_id,
            run_id=None,
            endpoint="/api/chat/stream",
            event="error",
            status="error",
            error=error,
        )
        self._logger.error("chat.log.stream.error user_id=%s thread_id=%s error=%s", user_id, thread_id, error)

    def extract_run_id(self, value: Any) -> str | None:
        for mapping in self._iter_mappings(value):
            candidate = mapping.get("run_id")
            if isinstance(candidate, str) and candidate:
                return candidate
        return None

    def _iter_mappings(self, value: Any):
        if isinstance(value, dict):
            yield value
            for item in value.values():
                yield from self._iter_mappings(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from self._iter_mappings(item)
