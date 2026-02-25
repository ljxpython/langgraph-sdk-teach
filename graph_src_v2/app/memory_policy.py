from __future__ import annotations

from dataclasses import dataclass

from graph_src_v2.config import AppRuntimeConfig


@dataclass(frozen=True)
class PersistencePolicyTemplate:
    name: str
    memory_backend: str
    store_backend: str


POLICY_TEMPLATES: dict[str, PersistencePolicyTemplate] = {
    "dev": PersistencePolicyTemplate(name="dev", memory_backend="memory", store_backend="memory"),
    "prod": PersistencePolicyTemplate(name="prod", memory_backend="postgres", store_backend="redis"),
    "stateless": PersistencePolicyTemplate(name="stateless", memory_backend="memory", store_backend="none"),
    "durable": PersistencePolicyTemplate(name="durable", memory_backend="postgres", store_backend="redis"),
}


def resolve_policy_template(name: str | None) -> PersistencePolicyTemplate | None:
    if not name:
        return None
    return POLICY_TEMPLATES.get(name.strip().lower())


def apply_persistence_policy(options: AppRuntimeConfig) -> AppRuntimeConfig:
    template = resolve_policy_template(options.persistence_profile)
    if template is None:
        return options

    options.memory_backend = template.memory_backend
    options.store_backend = template.store_backend
    return options
