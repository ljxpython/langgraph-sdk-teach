from __future__ import annotations

from typing import Any, Callable, Literal, cast

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call
from langchain.messages import ToolMessage
from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from langgraph.types import Command
from typing_extensions import NotRequired

from graph_src_v2.agents.customer_support_agent.prompts import (
    ISSUE_CLASSIFIER_PROMPT,
    RESOLUTION_SPECIALIST_PROMPT,
    WARRANTY_COLLECTOR_PROMPT,
)

SupportStep = Literal["warranty_collector", "issue_classifier", "resolution_specialist"]
WarrantyStatus = Literal["in_warranty", "out_of_warranty"]
IssueType = Literal["hardware", "software"]


class SupportState(AgentState):
    current_step: NotRequired[SupportStep]
    warranty_status: NotRequired[WarrantyStatus]
    issue_type: NotRequired[IssueType]


@tool("record_warranty_status", description="Record warranty status and move to issue classification.")
def record_warranty_status(status: WarrantyStatus, runtime: ToolRuntime[None, SupportState]) -> Command:
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded as: {status}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "warranty_status": status,
            "current_step": "issue_classifier",
        }
    )


@tool("record_issue_type", description="Record issue type and move to resolution step.")
def record_issue_type(issue_type: IssueType, runtime: ToolRuntime[None, SupportState]) -> Command:
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Issue type recorded as: {issue_type}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "issue_type": issue_type,
            "current_step": "resolution_specialist",
        }
    )


@tool("escalate_to_human", description="Escalate the case to human support with a reason.")
def escalate_to_human(reason: str) -> str:
    return f"Escalating to human support. Reason: {reason}"


@tool("provide_solution", description="Provide a concrete solution to the customer.")
def provide_solution(solution: str) -> str:
    return f"Solution provided: {solution}"


STEP_CONFIG: dict[SupportStep, dict[str, Any]] = {
    "warranty_collector": {
        "prompt": WARRANTY_COLLECTOR_PROMPT,
        "tools": [record_warranty_status],
        "requires": [],
    },
    "issue_classifier": {
        "prompt": ISSUE_CLASSIFIER_PROMPT,
        "tools": [record_issue_type],
        "requires": ["warranty_status"],
    },
    "resolution_specialist": {
        "prompt": RESOLUTION_SPECIALIST_PROMPT,
        "tools": [provide_solution, escalate_to_human],
        "requires": ["warranty_status", "issue_type"],
    },
}


@wrap_model_call
def apply_step_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    current_step = request.state.get("current_step", "warranty_collector")
    step = str(current_step)
    if step not in STEP_CONFIG:
        raise ValueError(f"Unknown support step: {step}")

    config = cast(dict[str, Any], STEP_CONFIG[cast(SupportStep, step)])
    for key in config["requires"]:
        if request.state.get(key) is None:
            raise ValueError(f"{key} must be set before reaching {step}")

    system_prompt = str(config["prompt"]).format(**request.state)
    return handler(
        request.override(
            system_prompt=system_prompt,
            tools=list(config["tools"]),
        )
    )


def build_customer_support_agent(model: Any) -> Any:
    all_tools = [
        record_warranty_status,
        record_issue_type,
        provide_solution,
        escalate_to_human,
    ]
    return create_agent(
        model=model,
        tools=all_tools,
        state_schema=SupportState,
        middleware=[apply_step_config],
        name="customer_support_handoff_demo",
    )
