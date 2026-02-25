# deepagent_agent

Owner: deepagent scenario maintainers.

Files:

- `graph.py`: pure graph-native compiled graph export.
- `state.py`: context typing.
- `prompts.py`: prompt constants.
- `tools.py`: deepagent-specific skill/subagent declarations.

Rule:

- Keep deepagent-specific orchestration here.
- Shared runtime/mcp/tools infrastructure remains outside this directory.
