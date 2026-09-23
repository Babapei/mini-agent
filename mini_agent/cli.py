"""命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mini_agent.agent.loop import run_agent
from mini_agent.llm.base import LLMError
from mini_agent.llm.mock import MockLLM
from mini_agent.llm.openai_compatible import OpenAICompatibleLLM


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mini-agent", description="连续调用工具完成任务的 Mini Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="执行一个自然语言任务")
    run.add_argument("task", help="交给 Agent 的任务")
    run.add_argument("--workspace", default="workspace", help="工具可访问的根目录")
    run.add_argument("--llm", choices=("mock", "openai"), default="mock")
    run.add_argument("--max-steps", type=int, default=12, help="最大决策轮数")
    run.add_argument("--trace-dir", default="docs/traces", help="写入 trace.md 和 trace.jsonl 的目录")
    args = parser.parse_args(argv)
    return _run(args)


def _run(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"workspace 不存在：{workspace}", file=sys.stderr)
        return 2
    if args.max_steps < 1:
        print("最大轮数必须大于 0", file=sys.stderr)
        return 2
    try:
        llm = _build_llm(args.llm)
    except LLMError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    result = run_agent(
        args.task,
        workspace,
        llm,
        max_steps=args.max_steps,
        trace_dir=Path(args.trace_dir),
        system_prompt=_load_system_prompt(),
    )
    print(result.answer, flush=True)
    print(f"status: {result.status}", file=sys.stderr)
    print(f"steps: {result.steps}", file=sys.stderr)
    print(f"trace: {args.trace_dir}", file=sys.stderr)
    return 0


def _build_llm(name: str):
    if name == "mock":
        return MockLLM()
    return OpenAICompatibleLLM.from_env()


def _load_system_prompt() -> str:
    candidates = (
        Path("docs/prompts/system.md"),
        Path(__file__).resolve().parents[1] / "docs" / "prompts" / "system.md",
    )
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
