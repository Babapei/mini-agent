"""运行四个固定任务，以及能在本地确认的拓展项。"""

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
from mini_agent.tasks import TASKS, TODO_TASK
from mini_agent.tools.base import READ
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


E7_PROMPT = "先用 tool_search 查找哪个工具负责计算，再用它计算 1+1，不要自己心算。"
E8_PROMPT = "使用 delegate，把「用 calculator 计算 1+1」交给下一层。拿到子任务答案后，写入 out.md。"
LOCAL_PYTESTS = (
    "tests/test_loop.py::test_compression_keeps_the_latest_tool_result",
    "tests/test_loop.py::test_short_sales_task_is_not_compressed",
    "tests/test_tools.py::test_tool_search_finds_calculator_and_rejects_empty_query",
    "tests/test_loop.py::test_delegate_is_absent_for_the_default_todo_task",
    "tests/test_loop.py::test_delegate_runs_one_child_level",
    "tests/test_loop.py::test_failed_child_returns_to_parent_once",
    "tests/test_loop.py::test_stream_prints_tool_name_before_answer",
    "tests/test_loop.py::test_no_stream_prints_only_the_final_answer",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行四个固定任务和拓展项")
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
        results.extend(["固定句子检查只在 mock 下启用。真实模型的任务只记录。E4、E5、E8 的假模型检查两种模式都会跑。", ""])
    failures: list[str] = []
    ran: dict[str, object] = {}
    if args.llm == "mock":
        failures.extend(_run_e1(workspace, llm, trace_root, system_prompt, results, check=True))
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
        ran[task["kind"]] = result

    if args.llm == "mock":
        failures.extend(_check_trace_extensions(ran, results))
    else:
        failures.extend(_run_e1(workspace, llm, trace_root, system_prompt, results, check=False))
        _record_openai_extra(workspace, llm, trace_root, system_prompt, results)
    failures.extend(_run_local_pytests(results))

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


def _run_e1(workspace, llm, trace_root: Path, system_prompt: str, results: list[str], check: bool) -> list[str]:
    target = workspace / "todo-report.md"
    if target.exists() and not check:
        target.unlink()
    trace_dir = trace_root / "e1-readonly"
    result = run_agent(
        TODO_TASK,
        workspace,
        llm,
        trace_dir=trace_dir,
        system_prompt=system_prompt,
        allowed={READ},
    )
    problems: list[str] = []
    if check:
        if "权限不足：write_file 需要 write" not in result.trace_markdown:
            problems.append("e1: Trace 没有写明 write_file 缺少 write")
        if target.exists():
            problems.append("e1: 只读运行仍然创建了 todo-report.md")
        if "search_text" not in result.trace_markdown:
            problems.append("e1: 只读运行没有搜索")
    _append_section(results, "e1-readonly", result, trace_dir, "通过" if check and not problems else ("失败" if problems else "已记录"))
    if problems:
        results.extend(f"- {problem}" for problem in problems)
        results.append("")
    return problems


def _check_trace_extensions(ran: dict, results: list[str]) -> list[str]:
    problems: list[str] = []
    sales = ran["sales"].trace_markdown
    recovery = ran["recovery"].trace_markdown
    blocked = ran["blocked"].trace_markdown
    sales_headings = _headings(sales)
    recovery_headings = _headings(recovery)
    if "Plan" not in sales_headings or sales_headings.index("Plan") > sales_headings.index("Tool Call"):
        problems.append("e2: 销售额 Trace 的 Plan 不在第一次 Tool Call 之前")
    plan_text = sales.split("## Plan", 1)[1].split("##", 1)[0]
    if "101" in plan_text:
        problems.append("e2: 计划里写死了 101")
    if "Plan Update" not in recovery_headings:
        problems.append("e3: 恢复任务没有 Plan Update")
    elif recovery_headings.index("Plan Update") < recovery_headings.index("Tool Result"):
        problems.append("e3: Plan Update 出现在失败结果之前")
    if "Plan Update" in sales_headings:
        problems.append("e3: 销售额成功路径出现了 Plan Update")
    if "Recovery Hint" not in _headings(recovery):
        problems.append("e6: 恢复任务没有 Recovery Hint")
    if "Recovery Hint" in _headings(blocked):
        problems.append("e6: 越界任务出现了 Recovery Hint")
    results.extend(
        [
            "## e2-plan",
            "",
            "- 检查：" + ("通过" if not any(item.startswith("e2:") for item in problems) else "失败"),
            "- 看：四个任务里的 `## Plan`",
            "",
            "## e3-plan-update",
            "",
            "- 检查：" + ("通过" if not any(item.startswith("e3:") for item in problems) else "失败"),
            "- 看：`03-recovery` 有 `## Plan Update`，`02-sales` 没有",
            "",
            "## e6-recovery-hint",
            "",
            "- 检查：" + ("通过" if not any(item.startswith("e6:") for item in problems) else "失败"),
            "- 看：`03-recovery` 有 `## Recovery Hint`，`04-blocked` 没有",
            "",
        ]
    )
    return problems


def _record_openai_extra(workspace, llm, trace_root: Path, system_prompt: str, results: list[str]) -> None:
    for task_id, prompt, extra in (
        ("e7-tool-search", E7_PROMPT, {}),
        ("e8-sub-agent", E8_PROMPT, {"enable_delegate": True}),
    ):
        trace_dir = trace_root / task_id
        result = run_agent(prompt, workspace, llm, trace_dir=trace_dir, system_prompt=system_prompt, **extra)
        _append_section(results, task_id, result, trace_dir, "已记录")
    results.extend(
        [
            "## e2-plan",
            "",
            "- 检查：已记录",
            "- 看四个任务 Trace 里有没有 `## Plan`。模型第一轮没写文字就不会有。",
            "",
            "## e3-plan-update",
            "",
            "- 检查：不适用",
            "- 真实模型不写 `## Plan Update`。这一项看 `docs/traces/mock/03-recovery/trace.md`。",
            "",
            "## e6-recovery-hint",
            "",
            "- 检查：已记录",
            "- 看 `03-recovery` 或 `02-sales` 里缺文件之后有没有 `## Recovery Hint`。",
            "",
        ]
    )


def _run_local_pytests(results: list[str]) -> list[str]:
    import pytest

    code = pytest.main(["-q", "--tb=line", *LOCAL_PYTESTS])
    ok = code == 0
    results.extend(
        [
            "## e4-e5-e7-e8-local",
            "",
            f"- 检查：{'通过' if ok else '失败'}",
            "- E4 压缩、E5 打印顺序、E7 查找工具、E8 一层子代理。这些不访问网络。",
            "",
        ]
    )
    if ok:
        return []
    return ["e4-e5-e7-e8: 本地自动测试没有通过"]


def _append_section(results: list[str], task_id: str, result, trace_dir: Path, status: str) -> None:
    results.extend(
        [
            f"## {task_id}",
            "",
            f"- 状态：{result.status}",
            f"- 检查：{status}",
            f"- 轮数：{result.steps}",
            f"- Trace：`{trace_dir / 'trace.md'}`",
            "",
            result.answer,
            "",
        ]
    )


def _headings(markdown: str) -> list[str]:
    return re.findall(r"^## (.+)$", markdown, re.MULTILINE)


def _system_prompt() -> str:
    path = ROOT / "docs" / "prompts" / "system.md"
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
