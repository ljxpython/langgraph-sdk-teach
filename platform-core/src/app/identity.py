from __future__ import annotations

from fastapi import HTTPException
from fastapi import Request


def parse_bearer_identity(authorization: str) -> tuple[str, str]:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ValueError("invalid authorization scheme")

    token = authorization[len(prefix) :].strip()
    if not token:
        raise ValueError("missing bearer token")

    pairs = [part.strip() for part in token.split(";") if part.strip()]
    if len(pairs) != 2:
        raise ValueError("invalid identity format")

    values: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition(":")
        if sep != ":":
            raise ValueError("invalid identity pair")
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError("invalid identity value")
        values[key] = value

    tenant_id = values.get("tenant")
    user_id = values.get("user")
    if not tenant_id or not user_id or len(values) != 2:
        raise ValueError("tenant/user is required")
    return tenant_id, user_id


def require_identity(request: Request) -> tuple[str, str]:
    authorization = request.headers.get("Authorization")
    if not authorization:
        tenant_id = "local-dev"
        user_id = "local-dev"
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id
        return tenant_id, user_id

    try:
        tenant_id, user_id = parse_bearer_identity(authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc

    request.state.tenant_id = tenant_id
    request.state.user_id = user_id
    return tenant_id, user_id
