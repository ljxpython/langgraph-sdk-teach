# assistant_agent

Owner: execution-layer agent maintainers.

Files:

- `graph.py`: LangGraph runtime graph entry (`agent`, `make_graph`).
- `state.py`: runtime context/state typing for this agent.
- `prompts.py`: prompt constants.
- `tools.py`: tool surface assembly for this agent.

Rule:

- Put assistant-specific logic in this directory.
- Keep shared execution concerns in `graph_src_v1/app`, `graph_src_v1/mcp`, and `graph_src_v1/tools`.
