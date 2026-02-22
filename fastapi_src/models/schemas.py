from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ThreadRequest(BaseModel):
    user_id: str = Field(min_length=1)
    api_url: str | None = None


class WaitChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    assistant_id: str | None = None
    api_url: str | None = None
    context: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class ResumeChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    command: dict[str, Any]
    assistant_id: str | None = None
    api_url: str | None = None
