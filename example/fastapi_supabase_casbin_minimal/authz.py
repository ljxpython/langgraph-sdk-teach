from __future__ import annotations

from functools import lru_cache

import casbin
from casbin import util

from .auth import UserClaims
from .config import get_settings


@lru_cache(maxsize=1)
def get_enforcer() -> casbin.Enforcer:
    settings = get_settings()
    enforcer = casbin.Enforcer(settings.casbin_model_path, settings.casbin_policy_path)
    enforcer.add_function("keyMatch2", util.key_match2)
    enforcer.add_function("regexMatch", util.regex_match)
    return enforcer


def _role_subject(role: str) -> str:
    return f"role:{role}"


def enforce_action(*, user: UserClaims, obj: str, act: str) -> bool:
    enforcer = get_enforcer()
    if enforcer.enforce(_role_subject(user.role), obj, act):
        return True
    return bool(enforcer.enforce(user.user_id, obj, act))
