from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    langgraph_api_url: str
    default_assistant_id: str
    sqlite_path: str
    default_stream_mode: str
    cors_origins: list[str]


def get_settings() -> Settings:
    default_origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
    raw_origins = os.getenv("FASTAPI_CORS_ORIGINS", ",".join(default_origins))
    extra_origins = [x.strip() for x in raw_origins.split(",") if x.strip()]
    cors_origins = sorted(set(default_origins + extra_origins))
    return Settings(
        langgraph_api_url=os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:8123"),
        default_assistant_id=os.getenv("LANGGRAPH_ASSISTANT_ID", "agent"),
        sqlite_path=os.getenv("FASTAPI_SQLITE_PATH", "fastapi_src/data/app.db"),
        default_stream_mode=os.getenv("FASTAPI_DEFAULT_STREAM_MODE", "messages,updates,tasks,checkpoints,debug"),
        cors_origins=cors_origins,
    )
