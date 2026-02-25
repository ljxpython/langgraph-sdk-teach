from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage


@dataclass
class ToolErrorGuardMiddleware(AgentMiddleware):
    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]) -> Any:
        try:
            return handler(request)
        except Exception as exc:
            return ToolMessage(
                content=f"Tool error: {exc}",
                tool_call_id=request.tool_call["id"],
            )

    async def awrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Awaitable[Any]]) -> Any:
        try:
            return await handler(request)
        except Exception as exc:
            return ToolMessage(
                content=f"Tool error: {exc}",
                tool_call_id=request.tool_call["id"],
            )
