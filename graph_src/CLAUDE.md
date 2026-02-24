# graph_src Architecture

## Directory Tree

```text
graph_src/
├── auth.py
├── agent.py
├── deepagent_example.py
├── llms.py
├── local_mcp_server.py
├── local_text_mcp_server.py
└── skills/
    ├── common/SKILL.md
    └── research/SKILL.md
```

## File Responsibilities

- `auth.py`: LangGraph custom auth implementation (`@auth.authenticate` + `@auth.on*`) for demo tokens, permission checks, and owner-based thread filtering.
- `agent.py`: Standard LangGraph runtime graph with configurable local tools and MCP tools.
- `deepagent_example.py`: Official-style DeepAgent reference graph showing Todo planning, skills loading, subagent delegation, and HITL interrupt parsing helpers.
- `llms.py`: Model factory helpers used by graph builders.
- `local_mcp_server.py`: Local math MCP tool server.
- `local_text_mcp_server.py`: Local text MCP tool server.
- `skills/common/SKILL.md`: Baseline workflow skill for planning + filesystem + verification.
- `skills/research/SKILL.md`: Delegated research workflow skill for subagent-based evidence gathering.

## Dependency and Boundaries

- `langgraph.json` points auth path to `graph_src/auth.py:custom_auth`; auth logic is enforced at platform access layer before graph execution.
- `deepagent_example.py` reuses `resolve_model` from `agent.py` to keep model behavior consistent.
- `deepagent_example.py` scopes filesystem access to `graph_src/` via `FilesystemBackend(root_dir=graph_src)`.
- HITL behavior is configured in-graph with `interrupt_on`; callers should inspect `__interrupt__` and resume with `Command(resume=...)`.
