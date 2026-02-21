from __future__ import annotations

import argparse
import asyncio
from typing import Any, Awaitable, Callable

from langgraph_sdk import get_client

from langgraph_sdk_learn_assistants import register as register_assistants
from langgraph_sdk_learn_common import DEFAULT_ASSISTANT_ID, DEFAULT_URL
from langgraph_sdk_learn_runs import register as register_runs
from langgraph_sdk_learn_threads import register as register_threads

Handler = Callable[[Any, argparse.Namespace], Awaitable[None]]


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, Handler]]:
    parser = argparse.ArgumentParser(description="LangGraph Python SDK 学习脚本")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_runtime_args(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--url", default=DEFAULT_URL, help="LangGraph API URL")
        subparser.add_argument("--assistant-id", default=DEFAULT_ASSISTANT_ID, help="assistant_id 或 graph_id")

    handlers: dict[str, Handler] = {}
    handlers.update(register_assistants(subparsers, add_runtime_args))
    handlers.update(register_threads(subparsers, add_runtime_args))
    handlers.update(register_runs(subparsers, add_runtime_args))
    return parser, handlers


async def async_main() -> None:
    parser, handlers = build_parser()
    args = parser.parse_args()
    client = get_client(url=args.url)

    handler = handlers.get(args.command)
    if handler is None:
        raise ValueError(f"未知命令: {args.command}")
    await handler(client, args)


if __name__ == "__main__":
    asyncio.run(async_main())
