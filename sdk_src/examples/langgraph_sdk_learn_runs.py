from __future__ import annotations

import argparse
import json
from typing import Any, Awaitable, Callable

from langgraph_sdk_learn_common import pretty

Handler = Callable[[Any, argparse.Namespace], Awaitable[None]]


def register(subparsers: Any, add_runtime_args: Callable[[argparse.ArgumentParser], None]) -> dict[str, Handler]:
    run_create = subparsers.add_parser("run-create", help="创建 run（非阻塞）")
    add_runtime_args(run_create)
    run_create.add_argument("--thread-id", default=None, help="可选：目标 thread_id；不传表示无状态 run")
    run_create.add_argument("--message", default="你好", help="用户输入（与 --input-json 二选一，后者优先）")
    run_create.add_argument("--input-json", default=None, help="输入 JSON，例: {\"messages\":[{\"role\":\"human\",\"content\":\"你好\"}]}")
    run_create.add_argument("--config-json", default=None, help="config JSON")
    run_create.add_argument("--context-json", default=None, help="context JSON")
    run_create.add_argument("--metadata-json", default=None, help="metadata JSON")
    run_create.add_argument("--interrupt-before", default=None, help="逗号分隔节点名，或 all")
    run_create.add_argument("--interrupt-after", default=None, help="逗号分隔节点名，或 all")

    run_list = subparsers.add_parser("run-list", help="列出 thread 下 runs")
    add_runtime_args(run_list)
    run_list.add_argument("--thread-id", required=True, help="目标 thread_id")
    run_list.add_argument("--limit", type=int, default=10, help="返回条数")
    run_list.add_argument("--offset", type=int, default=0, help="偏移")
    run_list.add_argument("--status", default=None, help="pending/running/error/success/timeout/interrupted")

    run_get = subparsers.add_parser("run-get", help="获取 run 详情")
    add_runtime_args(run_get)
    run_get.add_argument("--thread-id", required=True, help="目标 thread_id")
    run_get.add_argument("--run-id", required=True, help="目标 run_id")

    run_cancel = subparsers.add_parser("run-cancel", help="取消 run")
    add_runtime_args(run_cancel)
    run_cancel.add_argument("--thread-id", required=True, help="目标 thread_id")
    run_cancel.add_argument("--run-id", required=True, help="目标 run_id")
    run_cancel.add_argument("--wait", action="store_true", help="是否等待取消完成")
    run_cancel.add_argument("--action", default="interrupt", help="取消动作，默认 interrupt")

    run_join = subparsers.add_parser("run-join", help="等待 run 完成并返回结果")
    add_runtime_args(run_join)
    run_join.add_argument("--thread-id", required=True, help="目标 thread_id")
    run_join.add_argument("--run-id", required=True, help="目标 run_id")

    run_join_stream = subparsers.add_parser("run-join-stream", help="重新加入已有 run 的流")
    add_runtime_args(run_join_stream)
    run_join_stream.add_argument("--thread-id", required=True, help="目标 thread_id")
    run_join_stream.add_argument("--run-id", required=True, help="目标 run_id")
    run_join_stream.add_argument("--stream-mode", default=None, help="逗号分隔 stream_mode")

    wait_run = subparsers.add_parser("wait-run", help="执行 runs.wait")
    add_runtime_args(wait_run)
    wait_run.add_argument("--thread-id", default=None, help="可选：目标 thread_id；不传表示无状态 wait")
    wait_run.add_argument("--message", default="你好", help="用户输入（与 --input-json 二选一，后者优先）")
    wait_run.add_argument("--input-json", default=None, help="输入 JSON")
    wait_run.add_argument("--config-json", default=None, help="config JSON")
    wait_run.add_argument("--context-json", default=None, help="context JSON")
    wait_run.add_argument("--metadata-json", default=None, help="metadata JSON")
    wait_run.add_argument("--interrupt-before", default=None, help="逗号分隔节点名，或 all")
    wait_run.add_argument("--interrupt-after", default=None, help="逗号分隔节点名，或 all")

    stream_run = subparsers.add_parser("stream-run", help="执行 runs.stream")
    add_runtime_args(stream_run)
    stream_run.add_argument("--thread-id", default=None, help="可选：目标 thread_id；不传表示无状态 stream")
    stream_run.add_argument("--message", default="你好", help="用户输入（与 --input-json 二选一，后者优先）")
    stream_run.add_argument("--input-json", default=None, help="输入 JSON")
    stream_run.add_argument("--config-json", default=None, help="config JSON")
    stream_run.add_argument("--context-json", default=None, help="context JSON")
    stream_run.add_argument("--metadata-json", default=None, help="metadata JSON")
    stream_run.add_argument("--interrupt-before", default=None, help="逗号分隔节点名，或 all")
    stream_run.add_argument("--interrupt-after", default=None, help="逗号分隔节点名，或 all")
    stream_run.add_argument(
        "--stream-mode",
        default="updates,messages,tasks,checkpoints,debug",
        help="逗号分隔的 stream_mode",
    )

    full_demo = subparsers.add_parser("full-demo", help="最小全链路演示")
    add_runtime_args(full_demo)
    full_demo.add_argument("--message", default="你好", help="用户输入")

    return {
        "run-create": handle_run_create,
        "run-list": handle_run_list,
        "run-get": handle_run_get,
        "run-cancel": handle_run_cancel,
        "run-join": handle_run_join,
        "run-join-stream": handle_run_join_stream,
        "wait-run": handle_wait_run,
        "stream-run": handle_stream_run,
        "full-demo": handle_full_demo,
    }


def parse_json_field(raw: str | None, field: str) -> Any:
    # 将命令行传入的 JSON 字符串解析为对象。
    # 主要用于 input/config/context/metadata 等可覆盖参数。
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field} 不是合法 JSON") from exc


def parse_interrupt(raw: str | None) -> Any:
    # 将中断参数转为 SDK 需要的格式：
    # - all -> "all"
    # - node_a,node_b -> ["node_a", "node_b"]
    if raw is None:
        return None
    if raw.strip().lower() == "all":
        return "all"
    values = [x.strip() for x in raw.split(",") if x.strip()]
    return values if values else None


def resolve_input(args: argparse.Namespace) -> Any:
    # 输入优先级：--input-json > --message
    # 默认消息格式与 Agent Server 文档一致：{"messages": [...]}。
    input_json = parse_json_field(args.input_json, "--input-json")
    if input_json is not None:
        return input_json
    return {"messages": [{"role": "human", "content": args.message}]}


def run_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    # 统一组装 Run 请求体中的可覆盖字段。
    # 对应 REST 请求体常见字段：input/config/context/metadata/interrupt_before/interrupt_after。
    kwargs: dict[str, Any] = {
        "input": resolve_input(args),
        "config": parse_json_field(getattr(args, "config_json", None), "--config-json"),
        "context": parse_json_field(getattr(args, "context_json", None), "--context-json"),
        "metadata": parse_json_field(getattr(args, "metadata_json", None), "--metadata-json"),
        "interrupt_before": parse_interrupt(getattr(args, "interrupt_before", None)),
        "interrupt_after": parse_interrupt(getattr(args, "interrupt_after", None)),
    }
    return {k: v for k, v in kwargs.items() if v is not None}


def parse_stream_mode(raw: str | None) -> Any:
    # 解析 stream_mode: "updates,messages" -> ["updates", "messages"]
    if raw is None:
        return None
    values = [x.strip() for x in raw.split(",") if x.strip()]
    return values if values else None


async def handle_run_create(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /runs 或 POST /threads/{thread_id}/runs
    # 作用: 创建 run（非阻塞），立即返回 run_id，后续可 list/get/join。
    # 主要参数:
    # - thread_id: 可选，不传为无状态 run
    # - assistant_id: 必填，可传 graph_id 或 assistant UUID
    # - input/config/context/metadata/interrupt_before/interrupt_after: 可选覆盖项
    result = await client.runs.create(args.thread_id, args.assistant_id, **run_kwargs(args))
    print(pretty(result))


async def handle_run_list(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}/runs
    # 作用: 列出某个 thread 下的运行记录。
    # 主要参数: thread_id(必填), limit/offset/status(可选过滤)。
    result = await client.runs.list(args.thread_id, limit=args.limit, offset=args.offset, status=args.status)
    print(pretty(result))


async def handle_run_get(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}/runs/{run_id}
    # 作用: 查询单个 run 的详细信息（状态、参数、时间等）。
    # 主要参数: thread_id, run_id（都必填）。
    result = await client.runs.get(args.thread_id, args.run_id)
    print(pretty(result))


async def handle_run_cancel(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /threads/{thread_id}/runs/{run_id}/cancel
    # 作用: 取消正在执行的 run。
    # 主要参数:
    # - thread_id/run_id: 定位 run
    # - wait: 是否等待取消完成
    # - action: 默认 interrupt
    await client.runs.cancel(args.thread_id, args.run_id, wait=args.wait, action=args.action)
    print(pretty({"cancelled": args.run_id, "thread_id": args.thread_id, "wait": args.wait, "action": args.action}))


async def handle_run_join(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}/runs/{run_id}/join
    # 作用: 等待已创建 run 完成并返回结果（常配合 run-create 使用）。
    # 主要参数: thread_id, run_id。
    result = await client.runs.join(args.thread_id, args.run_id)
    print(pretty(result))


async def handle_run_join_stream(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: GET /threads/{thread_id}/runs/{run_id}/stream
    # 作用: 重新接入某个已有 run 的事件流（断线续看常用）。
    # 主要参数: thread_id, run_id, stream_mode(可选)。
    stream_mode = parse_stream_mode(args.stream_mode)
    async for chunk in client.runs.join_stream(args.thread_id, args.run_id, stream_mode=stream_mode):
        print(f"event={chunk.event}")
        print(pretty(chunk.data))


async def handle_wait_run(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /runs/wait 或 POST /threads/{thread_id}/runs/wait
    # 作用: 创建并等待 run 完成，直接拿最终结果（非流式）。
    # 主要参数:
    # - assistant_id: 必填
    # - thread_id: 可选（不传无状态）
    # - input/config/context/metadata/interrupt_before/interrupt_after: 可选
    result = await client.runs.wait(
        args.thread_id,
        args.assistant_id,
        **run_kwargs(args),
    )
    print(pretty(result))


async def handle_stream_run(client: Any, args: argparse.Namespace) -> None:
    # 对应 cURL: POST /runs/stream 或 POST /threads/{thread_id}/runs/stream
    # 作用: 创建并流式输出 run 执行过程（学习与调试首选）。
    # 主要参数:
    # - assistant_id: 必填
    # - thread_id: 可选（不传无状态）
    # - stream_mode: events 粒度选择（updates/messages/tasks/checkpoints/debug 等）
    # - 其余可覆盖项与 wait-run 相同
    stream_mode = parse_stream_mode(args.stream_mode) or ["updates", "messages", "tasks", "checkpoints", "debug"]
    async for chunk in client.runs.stream(
        args.thread_id,
        args.assistant_id,
        **run_kwargs(args),
        stream_mode=stream_mode,
    ):
        print(f"event={chunk.event}")
        print(pretty(chunk.data))


async def handle_full_demo(client: Any, args: argparse.Namespace) -> None:
    # 教学闭环: assistants.search -> threads.create -> runs.wait -> threads.get_state
    # 作用: 一条命令跑通最小学习链路。
    print("[1/4] assistants.search")
    assistants = await client.assistants.search(limit=10, offset=0)
    print(f"assistants_count={len(assistants)}")

    print("[2/4] threads.create")
    thread = await client.threads.create()
    thread_id = thread["thread_id"]
    print(f"thread_id={thread_id}")

    print("[3/4] runs.wait")
    run_result = await client.runs.wait(
        thread_id,
        args.assistant_id,
        input={"messages": [{"role": "human", "content": args.message}]},
    )
    print(pretty(run_result))

    print("[4/4] threads.get_state")
    state = await client.threads.get_state(thread_id)
    print(pretty(state))
