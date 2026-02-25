__all__ = ["agent", "make_graph", "deepagent_demo"]


def __getattr__(name: str):
    if name in {"agent", "make_graph"}:
        from graph_src_v1.agents.assistant_agent.graph import agent, make_graph

        return {"agent": agent, "make_graph": make_graph}[name]
    if name == "deepagent_demo":
        from graph_src_v1.agents.deepagent_agent.graph import deepagent_demo

        return deepagent_demo
    raise AttributeError(name)
