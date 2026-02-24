from __future__ import annotations

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException

from .auth import UserClaims
from .auth import get_current_user
from .authz import enforce_action
from .config import get_settings


settings = get_settings()
app = FastAPI(title="FastAPI + Supabase + Casbin Minimal")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
async def me(user: UserClaims = Depends(get_current_user)) -> dict[str, str | None]:
    return {
        "user_id": user.user_id,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "issuer": user.iss,
    }


@app.get("/api/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    user: UserClaims = Depends(get_current_user),
) -> dict[str, str]:
    if not enforce_action(user=user, obj=f"/api/threads/{thread_id}", act="GET"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"thread_id": thread_id, "owner": user.user_id, "mode": settings.environment}


@app.post("/api/threads")
async def create_thread(user: UserClaims = Depends(get_current_user)) -> dict[str, str]:
    if not enforce_action(user=user, obj="/api/threads", act="POST"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"message": "thread creation permitted", "user_id": user.user_id}
