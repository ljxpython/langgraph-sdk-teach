from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI

from graph_src_v1.config import AppRuntimeConfig


def _resolve_openai_compatible(
    *,
    model: str,
    api_key: str | None,
    base_url: str | None = None,
) -> ChatOpenAI:
    if not api_key:
        raise ValueError(f"Missing API key for model '{model}'.")
    kwargs: dict[str, Any] = {"model": model, "api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def resolve_model(
    model_provider: str,
    *,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
):
    provider = model_provider.strip().lower()

    if provider in {"deepseek", "mass_deepseek"}:
        return _resolve_openai_compatible(
            model=model_name or os.getenv("MASS_DEEPSEEKV32_MODEL") or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat",
            api_key=api_key or os.getenv("MASS_KIMI_KEY") or os.getenv("DEEPSEEK_API_KEY"),
            base_url=base_url or os.getenv("MASS_URL") or "https://api.deepseek.com/v1",
        )

    if provider in {"kimi", "mass_kimi"}:
        return _resolve_openai_compatible(
            model=model_name or os.getenv("MASS_KIMI_MODEL") or os.getenv("KIMI_MODEL") or "moonshot-v1-8k",
            api_key=api_key or os.getenv("MASS_KIMI_KEY") or os.getenv("KIMI_API_KEY"),
            base_url=base_url or os.getenv("MASS_URL") or os.getenv("KIMI_BASE_URL") or "https://api.moonshot.cn/v1",
        )

    if provider in {"openai", "gpt"}:
        return _resolve_openai_compatible(
            model=model_name or os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL") or None,
        )

    return _resolve_openai_compatible(
        model=model_name or os.getenv("MASS_GLM_4_MODEL") or os.getenv("GLM_MODEL") or "glm-4",
        api_key=api_key or os.getenv("MASS_KIMI_KEY") or os.getenv("GLM_API_KEY"),
        base_url=base_url or os.getenv("MASS_URL") or os.getenv("GLM_BASE_URL") or None,
    )


def apply_model_runtime_params(model: Any, options: AppRuntimeConfig) -> Any:
    kwargs: dict[str, Any] = {}
    if options.temperature is not None:
        kwargs["temperature"] = options.temperature
    if options.max_tokens is not None:
        kwargs["max_tokens"] = options.max_tokens
    if options.top_p is not None:
        kwargs["top_p"] = options.top_p
    if not kwargs:
        return model
    return model.bind(**kwargs)
