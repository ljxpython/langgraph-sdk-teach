# assistant_agent

Owner: execution-layer agent maintainers.

Files:

- `graph.py`: pure graph-native compiled graph export (`graph`).
- `state.py`: runtime context/state typing for this agent.
- `prompts.py`: prompt constants.
- `tools.py`: tool surface assembly for this agent.

Rule:

- Put assistant-specific logic in this directory.
- Keep shared execution concerns in `graph_src_v2/app`, `graph_src_v2/mcp`, and `graph_src_v2/tools`.
