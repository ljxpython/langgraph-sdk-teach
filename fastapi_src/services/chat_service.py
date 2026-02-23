from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, cast

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

    def normalize_context_and_config(
        self,
        context: dict[str, Any] | None,
        config: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        normalized_context = dict(context) if isinstance(context, dict) else None
        normalized_config = dict(config) if isinstance(config, dict) else None

        if normalized_context is not None and normalized_config is not None:
            configurable = normalized_config.get("configurable")
            if isinstance(configurable, dict):
                for key, value in configurable.items():
                    if key not in normalized_context:
                        normalized_context[key] = value
                normalized_config.pop("configurable", None)
                self._logger.warning(
                    "chat.context_only_policy merged configurable into context and removed configurable"
                )

        if normalized_config is not None and len(normalized_config) == 0:
            normalized_config = None

        return normalized_context, normalized_config

    async def create_or_get_thread(self, user_id: str, api_url: str | None) -> tuple[str, bool]:
        existing = self._repo.get_thread_id(user_id)
        if existing:
            self._logger.info("chat.thread.reuse user_id=%s thread_id=%s", user_id, existing)
            return existing, False

        thread_id = await self._create_thread(user_id, api_url)
        return thread_id, True

    async def create_thread(
        self,
        *,
        api_url: str | None,
        user_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        create_kwargs: dict[str, Any] = {}
        if metadata is not None:
            create_kwargs["metadata"] = metadata
        created = await client.threads.create(**create_kwargs)
        thread_id = str(created["thread_id"])
        if user_id:
            self._repo.upsert_thread_id(user_id, thread_id)
        self._logger.info("chat.thread.create.explicit user_id=%s thread_id=%s", user_id, thread_id)
        return {"thread_id": thread_id, "created": True, "user_id": user_id}

    async def _create_thread(self, user_id: str, api_url: str | None) -> str:
        client = get_langgraph_client(self.resolve_api_url(api_url))
        created = await client.threads.create()
        thread_id = str(created["thread_id"])
        self._repo.upsert_thread_id(user_id, thread_id)
        self._logger.info("chat.thread.create user_id=%s thread_id=%s", user_id, thread_id)
        return thread_id

    async def ensure_thread(self, user_id: str, api_url: str | None) -> str:
        api = self.resolve_api_url(api_url)
        existing = self._repo.get_thread_id(user_id)
        if existing:
            client = get_langgraph_client(api)
            try:
                await client.threads.get(existing)
                return existing
            except Exception as exc:
                self._logger.warning(
                    "chat.thread.stale user_id=%s thread_id=%s reason=%s",
                    user_id,
                    existing,
                    type(exc).__name__,
                )
                return await self._create_thread(user_id, api)

        return await self._create_thread(user_id, api)

    async def ensure_thread_ref(self, *, user_id: str | None, thread_id: str | None, api_url: str | None) -> str:
        if thread_id:
            return thread_id
        if user_id:
            return await self.ensure_thread(user_id, api_url)
        raise HTTPException(status_code=400, detail="thread_id 或 user_id 至少提供一个")

    def resolve_existing_thread_ref(self, *, user_id: str | None, thread_id: str | None) -> str:
        if thread_id:
            return thread_id
        if user_id:
            mapped = self._repo.get_thread_id(user_id)
            if mapped:
                return mapped
            raise HTTPException(status_code=404, detail=f"No thread for user_id={user_id}")
        raise HTTPException(status_code=400, detail="thread_id 或 user_id 至少提供一个")

    async def wait_chat(
        self,
        user_id: str | None,
        thread_id: str | None,
        message: str,
        assistant_id: str | None,
        api_url: str | None,
        context: dict[str, Any] | None,
        config: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        assistant = self.resolve_assistant_id(assistant_id)
        context, config = self.normalize_context_and_config(context, config)
        resolved_thread_id = await self.ensure_thread_ref(user_id=user_id, thread_id=thread_id, api_url=api)
        client = get_langgraph_client(api)
        run_kwargs: dict[str, Any] = {
            "input": {"messages": [{"role": "human", "content": message}]},
        }
        if context is not None:
            run_kwargs["context"] = context
        if config is not None:
            run_kwargs["config"] = config
        self._logger.info("chat.wait.start user_id=%s thread_id=%s assistant_id=%s", user_id, resolved_thread_id, assistant)
        result = await client.runs.wait(resolved_thread_id, assistant, **run_kwargs)
        self.log_run_result(
            user_id=user_id or "thread-only",
            thread_id=resolved_thread_id,
            result=result,
            endpoint="/api/chat/wait",
            event="wait",
        )
        self._logger.info("chat.wait.done user_id=%s thread_id=%s", user_id, resolved_thread_id)
        return {"thread_id": resolved_thread_id, "result": result}

    async def resume_chat(
        self,
        user_id: str | None,
        thread_id: str | None,
        command: dict[str, Any],
        assistant_id: str | None,
        api_url: str | None,
    ) -> dict[str, Any]:
        resolved_thread_id: str
        if thread_id:
            resolved_thread_id = thread_id
        elif user_id:
            mapped = self._repo.get_thread_id(user_id)
            if not mapped:
                self._logger.warning("chat.resume.missing_thread user_id=%s", user_id)
                raise HTTPException(status_code=404, detail=f"No thread for user_id={user_id}")
            resolved_thread_id = mapped
        else:
            raise HTTPException(status_code=400, detail="thread_id 或 user_id 至少提供一个")

        api = self.resolve_api_url(api_url)
        assistant = self.resolve_assistant_id(assistant_id)
        client = get_langgraph_client(api)
        self._logger.info("chat.resume.start user_id=%s thread_id=%s assistant_id=%s", user_id, resolved_thread_id, assistant)
        wait_fn = cast(Any, client.runs.wait)
        result = await wait_fn(resolved_thread_id, assistant, input=None, command=command)
        self.log_run_result(
            user_id=user_id or "thread-only",
            thread_id=resolved_thread_id,
            result=result,
            endpoint="/api/chat/resume",
            event="resume",
        )
        self._logger.info("chat.resume.done user_id=%s thread_id=%s", user_id, resolved_thread_id)
        return {"thread_id": resolved_thread_id, "result": result}

    async def get_state(self, user_id: str | None, thread_id: str | None, api_url: str | None) -> dict[str, Any]:
        resolved_thread_id = self.resolve_existing_thread_ref(user_id=user_id, thread_id=thread_id)
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        state = await client.threads.get_state(resolved_thread_id)
        self._logger.info("chat.state.done user_id=%s thread_id=%s", user_id, resolved_thread_id)
        return {"thread_id": resolved_thread_id, "state": state}

    async def get_messages(self, user_id: str | None, thread_id: str | None, api_url: str | None, limit: int, offset: int) -> dict[str, Any]:
        resolved_thread_id = self.resolve_existing_thread_ref(user_id=user_id, thread_id=thread_id)
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        state = await client.threads.get_state(resolved_thread_id)
        messages = self._extract_messages_from_state(state)
        if limit > 0:
            if offset > 0:
                end = len(messages) - offset
            else:
                end = len(messages)
            start = max(0, end - limit)
            if end <= 0:
                messages = []
            else:
                messages = messages[start:end]
        self._logger.info("chat.messages.done user_id=%s thread_id=%s count=%s", user_id, resolved_thread_id, len(messages))
        return {"thread_id": resolved_thread_id, "items": messages}

    async def get_history(self, user_id: str | None, thread_id: str | None, api_url: str | None, limit: int) -> dict[str, Any]:
        resolved_thread_id = self.resolve_existing_thread_ref(user_id=user_id, thread_id=thread_id)
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        history = await client.threads.get_history(resolved_thread_id, limit=limit)
        self._logger.info("chat.history.done user_id=%s thread_id=%s count=%s", user_id, resolved_thread_id, len(history))
        return {"thread_id": resolved_thread_id, "items": history}

    def get_run_logs(self, user_id: str | None, thread_id: str | None) -> dict[str, Any]:
        if self._run_log_repo is None:
            return {"user_id": user_id, "thread_id": thread_id, "items": []}
        if thread_id:
            items = self._run_log_repo.list_by_thread(thread_id)
            self._logger.info("chat.run_logs thread_id=%s count=%s", thread_id, len(items))
            return {"thread_id": thread_id, "items": items}
        if user_id:
            items = self._run_log_repo.list_by_user(user_id)
            self._logger.info("chat.run_logs user_id=%s count=%s", user_id, len(items))
            return {"user_id": user_id, "items": items}
        raise HTTPException(status_code=400, detail="thread_id 或 user_id 至少提供一个")

    async def list_threads(self, *, api_url: str | None, limit: int, offset: int) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        items = await client.threads.search(limit=limit, offset=offset)
        normalized: list[dict[str, Any]] = []
        for raw in items:
            if not isinstance(raw, Mapping):
                continue
            thread_id = raw.get("thread_id")
            if not isinstance(thread_id, str) or not thread_id:
                continue
            normalized.append(
                {
                    "thread_id": thread_id,
                    "created_at": raw.get("created_at"),
                    "updated_at": raw.get("updated_at"),
                    "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), Mapping) else {},
                    "status": raw.get("status"),
                }
            )
        return {"items": normalized}

    async def list_assistants(
        self,
        *,
        api_url: str | None,
        graph_id: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        search_kwargs: dict[str, Any] = {"limit": limit, "offset": offset}
        if graph_id:
            search_kwargs["graph_id"] = graph_id

        raw_items = await client.assistants.search(**search_kwargs)
        items: list[dict[str, str | None]] = []
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            assistant_id = raw.get("assistant_id")
            if not isinstance(assistant_id, str) or not assistant_id:
                continue
            raw_graph_id = raw.get("graph_id")
            raw_name = raw.get("name")
            items.append(
                {
                    "assistant_id": assistant_id,
                    "graph_id": str(raw_graph_id) if raw_graph_id is not None else None,
                    "name": str(raw_name) if raw_name is not None else None,
                }
            )

        items.sort(key=lambda item: ((item.get("graph_id") or ""), item["assistant_id"]))
        self._logger.info(
            "chat.assistants.list api=%s graph_id=%s count=%s",
            api,
            graph_id,
            len(items),
        )
        return {"items": items}

    async def list_graph_ids(self, *, api_url: str | None) -> dict[str, list[str]]:
        api = self.resolve_api_url(api_url)
        graph_ids: set[str] = set(self._load_local_graph_ids())
        client = get_langgraph_client(api)
        try:
            raw_items = await client.assistants.search(limit=500, offset=0)
            for raw in raw_items:
                if not isinstance(raw, Mapping):
                    continue
                raw_graph_id = raw.get("graph_id")
                if isinstance(raw_graph_id, str) and raw_graph_id:
                    graph_ids.add(raw_graph_id)
        except Exception as exc:
            self._logger.warning("chat.graphs.remote_fallback_only reason=%s", type(exc).__name__)

        items = sorted(graph_ids)
        self._logger.info("chat.graphs.list api=%s count=%s", api, len(items))
        return {"items": items}

    async def get_assistant(self, *, assistant_id: str, api_url: str | None) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        raw = await client.assistants.get(assistant_id)
        item = self._normalize_assistant_item(raw)
        if item is None:
            raise HTTPException(status_code=404, detail=f"assistant_id={assistant_id} not found")
        self._logger.info("chat.assistant.get api=%s assistant_id=%s", api, assistant_id)
        return {"item": item}

    async def create_assistant(
        self,
        *,
        graph_id: str,
        api_url: str | None,
        name: str | None,
        description: str | None,
        config: dict[str, Any] | None,
        context: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        create_fn = cast(Any, client.assistants.create)
        create_kwargs: dict[str, Any] = {
            "name": name,
            "description": description,
            "config": config,
            "context": context,
            "metadata": metadata,
        }
        raw = await create_fn(graph_id, **create_kwargs)
        item = self._normalize_assistant_item(raw)
        if item is None:
            raise HTTPException(status_code=500, detail="create assistant returned invalid payload")
        self._logger.info("chat.assistant.create api=%s graph_id=%s assistant_id=%s", api, graph_id, item["assistant_id"])
        return {"item": item}

    async def update_assistant(
        self,
        *,
        assistant_id: str,
        api_url: str | None,
        graph_id: str | None,
        name: str | None,
        description: str | None,
        config: dict[str, Any] | None,
        context: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        update_fn = cast(Any, client.assistants.update)
        update_kwargs: dict[str, Any] = {
            "graph_id": graph_id,
            "name": name,
            "description": description,
            "config": config,
            "context": context,
            "metadata": metadata,
        }
        raw = await update_fn(assistant_id, **update_kwargs)
        item = self._normalize_assistant_item(raw)
        if item is None:
            raise HTTPException(status_code=500, detail="update assistant returned invalid payload")
        self._logger.info("chat.assistant.update api=%s assistant_id=%s", api, assistant_id)
        return {"item": item}

    async def delete_assistant(
        self,
        *,
        assistant_id: str,
        api_url: str | None,
        delete_threads: bool,
    ) -> dict[str, Any]:
        api = self.resolve_api_url(api_url)
        client = get_langgraph_client(api)
        await client.assistants.delete(assistant_id, delete_threads=delete_threads)
        self._logger.info(
            "chat.assistant.delete api=%s assistant_id=%s delete_threads=%s",
            api,
            assistant_id,
            delete_threads,
        )
        return {"assistant_id": assistant_id, "deleted": True, "delete_threads": delete_threads}

    def _normalize_assistant_item(self, raw: Any) -> dict[str, str | None] | None:
        if not isinstance(raw, Mapping):
            return None
        assistant_id = raw.get("assistant_id")
        if not isinstance(assistant_id, str) or not assistant_id:
            return None
        raw_graph_id = raw.get("graph_id")
        raw_name = raw.get("name")
        return {
            "assistant_id": assistant_id,
            "graph_id": str(raw_graph_id) if raw_graph_id is not None else None,
            "name": str(raw_name) if raw_name is not None else None,
        }

    def _load_local_graph_ids(self) -> list[str]:
        root_dir = Path(__file__).resolve().parents[2]
        config_path = root_dir / "langgraph.json"
        if not config_path.exists():
            return []
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._logger.warning("chat.graphs.load_local_failed reason=%s", type(exc).__name__)
            return []
        graphs = payload.get("graphs") if isinstance(payload, dict) else None
        if not isinstance(graphs, Mapping):
            return []
        items: list[str] = []
        for key in graphs.keys():
            if isinstance(key, str) and key:
                items.append(key)
        return sorted(items)

    def _extract_messages_from_state(self, state: Any) -> list[dict[str, Any]]:
        if not isinstance(state, Mapping):
            return []
        values = state.get("values")
        if not isinstance(values, Mapping):
            return []
        raw_messages = values.get("messages")
        if not isinstance(raw_messages, list):
            return []

        items: list[dict[str, Any]] = []
        for raw in raw_messages:
            normalized = self._normalize_message(raw)
            if normalized is not None:
                items.append(normalized)
        return items

    def _normalize_message(self, raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, Mapping):
            return None

        msg_type = str(raw.get("type") or raw.get("role") or "")
        role_map = {
            "human": "user",
            "user": "user",
            "ai": "ai",
            "assistant": "ai",
            "tool": "tool",
            "system": "system",
        }
        role = role_map.get(msg_type, msg_type or "unknown")

        content = raw.get("content")
        text = self._message_text(content)
        tool_call_id = raw.get("tool_call_id")
        message_id = raw.get("id")
        name = raw.get("name")
        tool_calls = raw.get("tool_calls") if isinstance(raw.get("tool_calls"), list) else None

        return {
            "id": str(message_id) if message_id is not None else None,
            "role": role,
            "type": msg_type,
            "content": content,
            "text": text,
            "tool_call_id": str(tool_call_id) if tool_call_id is not None else None,
            "name": str(name) if name is not None else None,
            "tool_calls": tool_calls,
        }

    def _message_text(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, Mapping):
                    text = item.get("text")
                    if isinstance(text, str) and text:
                        parts.append(text)
            return "\n".join([part for part in parts if part])
        return str(content)

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
