from __future__ import annotations

from dataclasses import dataclass

import requests
from fastapi import Header
from fastapi import HTTPException

from .config import get_settings


@dataclass(frozen=True)
class UserClaims:
    user_id: str
    role: str
    tenant_id: str | None
    iss: str | None


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authorization must be Bearer token")
    token = authorization[len(prefix) :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")
    return token


def _fetch_supabase_user(token: str) -> dict:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=500, detail="SUPABASE_URL/SUPABASE_ANON_KEY is not configured")

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": settings.supabase_anon_key,
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Supabase auth request failed: {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase token")
    return response.json()


async def get_current_user(authorization: str | None = Header(default=None)) -> UserClaims:
    token = _extract_bearer_token(authorization)
    payload = _fetch_supabase_user(token)
    app_metadata = payload.get("app_metadata") or {}
    user_metadata = payload.get("user_metadata") or {}

    user_id = payload.get("id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Supabase user payload missing id")

    role = app_metadata.get("role") or user_metadata.get("role") or "user"
    tenant_id = app_metadata.get("tenant_id") or user_metadata.get("tenant_id")
    iss = payload.get("aud")
    return UserClaims(
        user_id=user_id,
        role=str(role),
        tenant_id=str(tenant_id) if tenant_id is not None else None,
        iss=str(iss) if iss is not None else None,
    )
