from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict, cast

from langchain.agents import create_agent
from langchain_core.tools import tool
from langgraph.constants import END, START
from langgraph.graph import StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from graph_src_v2.agents.router_knowledge_base_agent.prompts import (
    CLASSIFIER_SYSTEM_PROMPT,
    GITHUB_AGENT_PROMPT,
    NOTION_AGENT_PROMPT,
    SLACK_AGENT_PROMPT,
    SYNTHESIS_SYSTEM_PROMPT,
)

Source = Literal["github", "notion", "slack"]


class AgentInput(TypedDict):
    query: str


class AgentOutput(TypedDict):
    source: Source
    result: str


class Classification(TypedDict):
    source: Source
    query: str


class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str


class ClassificationResult(BaseModel):
    classifications: list[Classification] = Field(
        description="Knowledge sources to invoke with source-specific sub-queries",
        min_length=1,
    )


@tool("search_code", description="Search GitHub code for implementation details.")
def search_code(query: str, repo: str = "main") -> str:
    return f"Found code matching '{query}' in {repo}: auth middleware in src/auth.py"


@tool("search_issues", description="Search GitHub issues for known discussions.")
def search_issues(query: str) -> str:
    return f"Found issues for '{query}': #142 API auth docs, #203 token refresh"


@tool("search_prs", description="Search pull requests for change history.")
def search_prs(query: str) -> str:
    return f"PRs for '{query}': #156 JWT support, #178 OAuth scope updates"


@tool("search_notion", description="Search Notion docs and team wiki pages.")
def search_notion(query: str) -> str:
    return f"Found Notion docs for '{query}': API Authentication Guide"


@tool("get_page", description="Read a specific Notion page by page id.")
def get_page(page_id: str) -> str:
    return f"Notion page {page_id}: setup steps and troubleshooting notes"


@tool("search_slack", description="Search Slack channels and threads.")
def search_slack(query: str) -> str:
    return f"Slack results for '{query}': #engineering recommends Bearer token flow"


@tool("get_thread", description="Read a specific Slack thread by thread id.")
def get_thread(thread_id: str) -> str:
    return f"Slack thread {thread_id}: API key rotation best practices"


def _message_to_text(message: Any) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                maybe = item.get("text")
                if isinstance(maybe, str) and maybe:
                    parts.append(maybe)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(message)


def build_router_workflow(model: Any) -> Any:
    router_llm = model

    github_agent = create_agent(
        model,
        tools=[search_code, search_issues, search_prs],
        system_prompt=GITHUB_AGENT_PROMPT,
        name="github_kb_agent",
    )
    notion_agent = create_agent(
        model,
        tools=[search_notion, get_page],
        system_prompt=NOTION_AGENT_PROMPT,
        name="notion_kb_agent",
    )
    slack_agent = create_agent(
        model,
        tools=[search_slack, get_thread],
        system_prompt=SLACK_AGENT_PROMPT,
        name="slack_kb_agent",
    )

    def classify_query(state: RouterState) -> dict[str, list[Classification]]:
        structured = router_llm.with_structured_output(ClassificationResult)
        result = structured.invoke(
            [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": state["query"]},
            ]
        )

        classifications = list(result.classifications)
        if not classifications:
            classifications = [{"source": "github", "query": state["query"]}]
        return {"classifications": classifications}

    def route_to_agents(state: RouterState) -> list[Send]:
        classifications = state.get("classifications", [])
        if not classifications:
            return [Send("github", {"query": state["query"]})]
        return [Send(item["source"], {"query": item["query"]}) for item in classifications]

    def query_github(state: AgentInput) -> dict[str, list[AgentOutput]]:
        result = github_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
        return {"results": [{"source": "github", "result": _message_to_text(result["messages"][-1])}]}

    def query_notion(state: AgentInput) -> dict[str, list[AgentOutput]]:
        result = notion_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
        return {"results": [{"source": "notion", "result": _message_to_text(result["messages"][-1])}]}

    def query_slack(state: AgentInput) -> dict[str, list[AgentOutput]]:
        result = slack_agent.invoke({"messages": [{"role": "user", "content": state["query"]}]})
        return {"results": [{"source": "slack", "result": _message_to_text(result["messages"][-1])}]}

    def synthesize_results(state: RouterState) -> dict[str, str]:
        results = state.get("results", [])
        if not results:
            return {"final_answer": "No results found from any knowledge source."}

        formatted = [f"From {item['source']}:\n{item['result']}" for item in results]
        synthesis = router_llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        f"{SYNTHESIS_SYSTEM_PROMPT}\n"
                        f"Original query: {state['query']}"
                    ),
                },
                {"role": "user", "content": "\n\n".join(formatted)},
            ]
        )
        return {"final_answer": _message_to_text(synthesis)}

    return (
        StateGraph(RouterState)
        .add_node("classify", classify_query)
        .add_node("github", query_github)
        .add_node("notion", query_notion)
        .add_node("slack", query_slack)
        .add_node("synthesize", synthesize_results)
        .add_edge(START, "classify")
        .add_conditional_edges("classify", route_to_agents, ["github", "notion", "slack"])
        .add_edge("github", "synthesize")
        .add_edge("notion", "synthesize")
        .add_edge("slack", "synthesize")
        .add_edge("synthesize", END)
        .compile(name="router_knowledge_base_core")
    )


def invoke_router_from_messages(workflow: Any, messages: list[Any]) -> dict[str, Any]:
    user_query = ""
    for message in reversed(messages):
        msg_type = getattr(message, "type", None)
        role = getattr(message, "role", None)
        if msg_type == "human" or role == "user":
            user_query = _message_to_text(message)
            break
    if not user_query:
        user_query = "Please summarize available knowledge base guidance."

    return cast(dict[str, Any], workflow.invoke({"query": user_query}))
