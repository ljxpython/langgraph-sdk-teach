from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ThreadRequest(BaseModel):
    user_id: str = Field(min_length=1)
    api_url: str | None = None


class ThreadCreateRequest(BaseModel):
    api_url: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] | None = None


class WaitChatRequest(BaseModel):
    user_id: str | None = None
    thread_id: str | None = None
    message: str = Field(min_length=1)
    assistant_id: str | None = None
    api_url: str | None = None
    context: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class ResumeChatRequest(BaseModel):
    user_id: str | None = None
    thread_id: str | None = None
    command: dict[str, Any]
    assistant_id: str | None = None
    api_url: str | None = None


class AssistantCreateRequest(BaseModel):
    graph_id: str = Field(min_length=1)
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    api_url: str | None = None


class AssistantUpdateRequest(BaseModel):
    graph_id: str | None = None
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    api_url: str | None = None
