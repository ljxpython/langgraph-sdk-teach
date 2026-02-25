# LangGraph Execution Layer Architecture

## Scope

- Only LangGraph execution-layer concerns are covered here.
- Platform control-plane concerns are intentionally excluded.

## Directory Tree

```text
graph_src_v1/
├── ARCHITECTURE.md
├── .env.example
├── langgraph.json
├── config/
│   ├── __init__.py
│   └── runtime.py
├── agents/
│   ├── __init__.py
│   ├── registry.py
│   ├── assistant_agent/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── prompts.py
│   │   ├── tools.py
│   │   ├── middleware.py
│   │   └── README.md
│   └── deepagent_agent/
│       ├── __init__.py
│       ├── graph.py
│       ├── state.py
│       ├── prompts.py
│       ├── tools.py
│       └── README.md
├── mcp/
│   ├── __init__.py
│   ├── servers.py
│   ├── loader.py
│   ├── local_math_server.py
│   └── local_text_server.py
├── tools/
│   ├── __init__.py
│   ├── local.py
│   └── registry.py
├── app/
│   ├── __init__.py
│   ├── factory.py
│   ├── interrupts.py
│   ├── memory_policy.py
│   ├── models.py
│   └── persistence.py
├── middlewares/
│   ├── __init__.py
│   ├── registry.py
│   ├── message_sanitizer.py
│   └── tool_error_guard.py
└── skills/
    ├── common/SKILL.md
    └── research/SKILL.md
```

## Ownership Boundaries

- MCP lives in `graph_src_v1/mcp/`.
- local tools live in `graph_src_v1/tools/local.py`.
- each concrete agent lives in `graph_src_v1/agents/`.

## Responsibilities

- `langgraph.json`: single source of truth for deployed graph entrypoints.
- `agents/assistant_agent/*`: assistant agent package.
- `agents/deepagent_agent/*`: deepagent package.
- `mcp/servers.py`: MCP server allowlist/spec definitions.
- `mcp/loader.py`: MCP client bootstrap and remote tool loading.
- `tools/local.py`: local tool implementations.
- `tools/registry.py`: local+MCP tool composition for runtime.
- `config/runtime.py`: runtime config contract and dynamic override merge.
- `middlewares/*`: middleware components and registry.
- `app/models.py`: model provider resolution and parameter binding.
- `app/interrupts.py`: interrupt payload normalization and resume adapter.
- `app/memory_policy.py`: persistence profile templates.
- `app/persistence.py`: checkpointer/store backend construction.
- `app/factory.py`: assembly root for runtime agent.

## Multi-Agent Maintenance Contract

- Add new agents by creating `graph_src_v1/agents/<agent_name>/`.
- Each agent package must include `graph.py`, `state.py`, `prompts.py`, `tools.py`, `README.md`, and `__init__.py`.
- Middleware is component-based: each agent selects middleware by name (`middlewares` config key); avoid global hard-binding.
- Register the entrypoint in `graph_src_v1/langgraph.json` using `./graph_src_v1/agents/<agent_name>/graph.py:<export>`.
- Add deployment exposure in `graph_src_v1/langgraph.json` only after agent module is stable.
- Keep shared execution concerns in `app/*`, `mcp/*`, `tools/*`; do not duplicate them in per-agent modules.

## Local Environment Management

- Yes: local debug should use `.env` with `langgraph dev`.
- `graph_src_v1/langgraph.json` loads `.env` for local runs.
- Use `graph_src_v1/.env.example` as the template and create your real `.env` from it.
- Keep production secrets in deployment environment variables, not committed `.env` files.
- `langgraph dev` can use Postgres/Redis by only setting env vars (`POSTGRES_DSN`, `REDIS_URL`) plus backend/profile keys.

## Runtime Profiles

- `dev`: `memory_backend=memory`, `store_backend=memory`.
- `production`: `memory_backend=postgres`, `store_backend=redis`.
- `persistence_profile` supports `dev|prod|stateless|durable`.

## Runtime Dynamic Overrides

v1 uses a context-first contract:

1. Prefer runtime `context` (from `ServerRuntime.execution_runtime.context`) for business runtime parameters.
2. Keep `RunnableConfig.configurable` as compatibility fallback only.
3. Use environment variables for deployment defaults.
4. Apply profile defaults last.

Multi-graph rule:

- `assistant` and `deepagent_demo` both use runtime factory entries (`make_graph(config, runtime)`) so each run can rebuild model/tools/skills from context.
- This keeps dynamic model routing and dynamic MCP/tools/skills behavior consistent across graph types.

Runtime-factory vs pure graph-native decision rule:

- Current default: runtime-factory for both graph types (Occam: one mental model).
- Re-evaluate every 2-4 weeks with concrete signals.
- Switch a graph class to pure compiled graph-native entry only when at least two signals keep recurring:
  - runtime-injected parameters cause repeated behavior drift and difficult replay.
  - onboarding cost is high because contributors must trace too many runtime indirections.
  - runtime variability blocks useful caching/performance optimization at scale.
  - stronger static contract/governance is required than runtime context can provide.
- Anti-patterns to avoid:
  - keeping runtime-factory and graph-native as equal primary paths for the same graph class.
  - treating runtime context as hidden control plane with too many opaque flags.
  - splitting by graph type before evidence shows runtime-factory is the bottleneck.

Supported keys:

- model routing: `model_provider`, `model_name`/`model`, `model_base_url`/`base_url`, `model_api_key`
- model params: `temperature`, `max_tokens`, `top_p`
- tool switches: `enable_local_tools`, `enable_local_mcp`, `mcp_servers`
- persistence: `memory_backend`, `store_backend`, `postgres_dsn`, `redis_url`, `persistence_profile`
- middleware: `middlewares` (comma-separated string or list)

## Runbook

Local:

```bash
APP_ENV=dev langgraph dev --config graph_src_v1/langgraph.json
```

Production style:

```bash
APP_ENV=production \
POSTGRES_DSN="postgresql://user:pass@host:5432/dbname" \
REDIS_URL="redis://host:6379/0" \
langgraph up --config graph_src_v1/langgraph.json
```

## Minimal Migration Checklist (v1)

1. Keep `graph_src_v1` imports self-contained (`graph_src_v1.*` only).
2. Keep `graph_src_v1/langgraph.json` entrypoints under `./graph_src_v1/...`.
3. Keep dynamic business parameters in runtime `context`.
4. Use `config` for execution controls (for example `recursion_limit`).
5. Keep `config.configurable` support only as compatibility fallback.

## Local Postgres and Redis with Docker

Create persistent volumes:

```bash
docker volume create langgraph_pg_data
docker volume create langgraph_redis_data
```

Start PostgreSQL (persistent data):

```bash
docker run -d \
  --name langgraph-pg \
  --restart unless-stopped \
  -e POSTGRES_USER=langgraph \
  -e POSTGRES_PASSWORD=langgraph \
  -e POSTGRES_DB=langgraph \
  -p 5432:5432 \
  -v langgraph_pg_data:/var/lib/postgresql/data \
  postgres:16
```

Start Redis (AOF persistence enabled):

```bash
docker run -d \
  --name langgraph-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  -v langgraph_redis_data:/data \
  redis:7 redis-server --appendonly yes
```

Stop services:

```bash
docker stop langgraph-pg langgraph-redis
```

Start stopped services:

```bash
docker start langgraph-pg langgraph-redis
```

Remove containers (data is kept in volumes):

```bash
docker rm -f langgraph-pg langgraph-redis
```

Remove volumes (destructive, deletes persisted data):

```bash
docker volume rm langgraph_pg_data langgraph_redis_data
```

Recommended local env values:

```bash
POSTGRES_DSN=postgresql://langgraph:langgraph@localhost:5432/langgraph
REDIS_URL=redis://localhost:6379/0
APP_ENV=production
```
