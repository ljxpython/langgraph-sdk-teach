from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    supabase_url: str
    supabase_anon_key: str
    casbin_model_path: str
    casbin_policy_path: str


def get_settings() -> Settings:
    root = Path(__file__).resolve().parent
    return Settings(
        environment=os.getenv("APP_ENV", "dev"),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        casbin_model_path=os.getenv("CASBIN_MODEL_PATH", str(root / "model.conf")),
        casbin_policy_path=os.getenv("CASBIN_POLICY_PATH", str(root / "policy.csv")),
    )
