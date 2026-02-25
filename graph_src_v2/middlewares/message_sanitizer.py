from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage


def _stringify_message_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


@dataclass
class MessageSanitizerMiddleware(AgentMiddleware):
    def _sanitize(self, request: ModelRequest) -> ModelRequest:
        sanitized: list[Any] = []
        for msg in getattr(request, "messages", []) or []:
            if isinstance(msg, BaseMessage):
                content = getattr(msg, "content", "")
                if not isinstance(content, str):
                    try:
                        msg = msg.model_copy(update={"content": _stringify_message_content(content)})
                    except Exception:
                        try:
                            msg.content = _stringify_message_content(content)
                        except Exception:
                            pass
            sanitized.append(msg)
        return request.override(messages=sanitized)

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
        return handler(self._sanitize(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._sanitize(request))
