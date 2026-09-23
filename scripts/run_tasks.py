"""运行固定任务并检查输出和 Trace。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mini_agent.agent.loop import run_agent
from mini_agent.llm.base import LLMError
from mini_agent.llm.mock import MockLLM, sales_expression
from mini_agent.llm.openai_compatible import OpenAICompatibleLLM
from mini_agent.tasks import TASKS
from mini_agent.tools.registry import ToolRegistry
from scripts.generate_workspace import generate


TRACE_SEQUENCE = (
    "User",
    "Agent Decision",
    "Tool Call",
    "Tool Result",
    "Agent Decision",
    "Tool Call",
    "Tool Result",
    "Final Answer",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行 Mini Agent 的固定任务")
    parser.add_argument("--llm", choices=("mock", "openai"), default="mock")
    parser.add_argument("--workspace", default="workspace")
    parser.add_argument("--trace-root", default="")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    trace_root = Path(args.trace_root) if args.trace_root else Path("docs/traces") / args.llm
    try:
        llm = MockLLM() if args.llm == "mock" else OpenAICompatibleLLM.from_env()
    except LLMError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    generate(workspace)

    system_prompt = _system_prompt()
    results: list[str] = [f"# {args.llm} 任务结果", ""]
    if args.llm != "mock":
        results.extend(["固定句子检查只在 mock 下启用。本次只记录真实模型的运行结果。", ""])
    failures: list[str] = []
    for task in TASKS:
        trace_dir = trace_root / task["id"]
        result = run_agent(
            task["prompt"],
            workspace,
            llm,
            trace_dir=trace_dir,
            system_prompt=system_prompt,
        )
        problems = _check(task, workspace, result) if args.llm == "mock" else []
        status = "通过" if not problems else "失败"
        if args.llm != "mock":
            status = "已记录"
        results.append(f"## {task['id']}")
        results.append("")
        results.append(f"- 状态：{result.status}")
        results.append(f"- 检查：{status}")
        results.append(f"- 轮数：{result.steps}")
        results.append(f"- Trace：`{trace_dir / 'trace.md'}`")
        results.append("")
        results.append(result.answer)
        results.append("")
        if problems:
            failures.extend(f"{task['id']}: {problem}" for problem in problems)
            results.append("问题：")
            results.extend(f"- {problem}" for problem in problems)
            results.append("")

    result_path = Path("docs/results") / f"{args.llm}.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text("\n".join(results).rstrip() + "\n", encoding="utf-8")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"已通过，结果写入 {result_path}")
    return 0


def _check(task: dict, workspace: Path, result) -> list[str]:
    """按 Mock 的固定写法验收。只给 --llm mock 调用。"""
    problems: list[str] = []
    headings = re.findall(r"^## (.+)$", result.trace_markdown, re.MULTILINE)
    sequence = (
        ("User", "Agent Decision", "Tool Call", "Tool Result", "Final Answer")
        if task["kind"] == "blocked"
        else TRACE_SEQUENCE
    )
    cursor = 0
    for title in sequence:
        if title not in headings[cursor:]:
            problems.append(f"Trace 缺少顺序中的 {title}")
            break
        cursor = headings.index(title, cursor) + 1
    if task["kind"] == "blocked":
        if result.status != "final":
            problems.append(f"越界任务状态应为 final，实际是 {result.status}")
        if "路径超出 workspace" not in result.answer:
            problems.append("越界任务的最终答案没有包含路径失败原因")
        return problems
    if result.status != "final":
        problems.append(f"状态应为 final，实际是 {result.status}")
        return problems
    output = workspace / task["output"]
    if not output.is_file():
        problems.append(f"没有生成 {task['output']}")
        return problems
    text = output.read_text(encoding="utf-8")
    if task["kind"] == "todo":
        for heading in ("## README.md", "## src/user.ts", "## docs/design.md"):
            if heading not in text:
                problems.append(f"TODO 报告缺少 {heading}")
    elif task["kind"] == "sales":
        expected = _expected_total(workspace)
        if f"销售额合计：{expected}" not in text:
            problems.append(f"销售报告合计不是计算器结果 {expected}")
    elif task["kind"] == "recovery":
        expected = _expected_total(workspace)
        if "data/missing.txt 读取失败" not in text:
            problems.append("汇总没有写缺失文件失败")
        if "src/order.ts" not in text or "运费未计入" not in text:
            problems.append("汇总没有写来自搜索结果的 FIXME")
        if f"合计：{expected}" not in text:
            problems.append(f"汇总销售额不是计算器结果 {expected}")
    return problems


def _expected_total(workspace: Path) -> str:
    registry = ToolRegistry(workspace)
    loaded = registry.execute("read_file", {"path": "data/sales.txt"})
    expression = sales_expression(loaded.output)
    calculated = registry.execute("calculator", {"expression": expression})
    if not calculated.ok:
        raise RuntimeError(calculated.error)
    return calculated.output


def _system_prompt() -> str:
    path = ROOT / "docs" / "prompts" / "system.md"
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
