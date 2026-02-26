from __future__ import annotations

from typing import Any, Callable, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain_core.tools import tool

from graph_src_v2.agents.skills_sql_assistant_agent.prompts import SQL_ASSISTANT_SYSTEM_PROMPT


class Skill(TypedDict):
    name: str
    description: str
    content: str


SKILLS: list[Skill] = [
    {
        "name": "sales_analytics",
        "description": "Schema and business rules for sales analytics (customers, orders, revenue).",
        "content": (
            "# Sales Analytics Schema\n\n"
            "## Tables\n"
            "customers(customer_id, name, email, signup_date, status, customer_tier)\n"
            "orders(order_id, customer_id, order_date, status, total_amount, sales_region)\n"
            "order_items(item_id, order_id, product_id, quantity, unit_price, discount_percent)\n\n"
            "## Business Logic\n"
            "- Revenue only includes completed orders.\n"
            "- High-value orders are total_amount > 1000.\n"
            "- CLV is sum(total_amount) of completed orders by customer."
        ),
    },
    {
        "name": "inventory_management",
        "description": "Schema and business rules for inventory and warehouse stock tracking.",
        "content": (
            "# Inventory Management Schema\n\n"
            "## Tables\n"
            "products(product_id, product_name, sku, category, unit_cost, reorder_point, discontinued)\n"
            "warehouses(warehouse_id, warehouse_name, location, capacity)\n"
            "inventory(inventory_id, product_id, warehouse_id, quantity_on_hand, last_updated)\n"
            "stock_movements(movement_id, product_id, warehouse_id, movement_type, quantity, movement_date, reference_number)\n\n"
            "## Business Logic\n"
            "- Reorder when total stock <= reorder_point.\n"
            "- Exclude discontinued products by default.\n"
            "- Stock valuation is quantity_on_hand * unit_cost."
        ),
    },
]


@tool("load_skill", description="Load full content for a named SQL business skill.")
def load_skill(skill_name: str) -> str:
    for skill in SKILLS:
        if skill["name"] == skill_name:
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"
    available = ", ".join(item["name"] for item in SKILLS)
    return f"Skill '{skill_name}' not found. Available skills: {available}"


class SkillMiddleware(AgentMiddleware):
    tools = [load_skill]

    def __init__(self) -> None:
        lines = [f"- {item['name']}: {item['description']}" for item in SKILLS]
        self._skills_prompt = "\n".join(lines)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        addendum = (
            "\n\n## Available Skills\n"
            f"{self._skills_prompt}\n\n"
            "Use load_skill when you need schema and business rules for a skill."
        )
        new_content = list(request.system_message.content_blocks) + [{"type": "text", "text": addendum}]
        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))


def build_skills_sql_assistant_agent(model: Any) -> Any:
    return create_agent(
        model=model,
        system_prompt=SQL_ASSISTANT_SYSTEM_PROMPT,
        middleware=[SkillMiddleware()],
        name="skills_sql_assistant_demo",
    )
