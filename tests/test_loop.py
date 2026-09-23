import re
from pathlib import Path

from mini_agent.agent.loop import run_agent
from mini_agent.llm.base import Decision, Message, ToolCall
from mini_agent.llm.mock import MockLLM
from mini_agent.tasks import SALES_TASK, TODO_TASK
from scripts.generate_workspace import generate


def _headings(markdown: str) -> list[str]:
    return re.findall(r"^## (.+)$", markdown, re.MULTILINE)


def test_todo_task_searches_then_writes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    result = run_agent(TODO_TASK, workspace, MockLLM(), trace_dir=tmp_path / "trace")

    assert result.status == "final"
    report = (workspace / "todo-report.md").read_text(encoding="utf-8")
    assert "## README.md" in report
    assert "## src/user.ts" in report
    assert "## docs/design.md" in report
    headings = _headings(result.trace_markdown)
    expected = [
        "User",
        "Agent Decision",
        "Tool Call",
        "Tool Result",
        "Agent Decision",
        "Tool Call",
        "Tool Result",
        "Final Answer",
    ]
    start = 0
    for title in expected:
        start = headings.index(title, start) + 1
    assert (tmp_path / "trace" / "trace.md").is_file()
    assert (tmp_path / "trace" / "trace.jsonl").is_file()


def test_sales_total_follows_calculator(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    (workspace / "data" / "sales.txt").write_text(
        "product,quantity,price\nA,3,3\nB,1,1\n",
        encoding="utf-8",
    )
    result = run_agent(SALES_TASK, workspace, MockLLM())
    report = (workspace / "report.md").read_text(encoding="utf-8")
    assert result.status == "final"
    assert "销售额合计：10" in report
    assert "表达式：3*3+1*1" in report
    assert "calculator" in result.trace_markdown


def test_repeated_failure_stops(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    class RepeatLLM:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del messages, tools
            return Decision(
                thought="再次读取同一个缺失文件",
                tool_calls=[ToolCall(name="read_file", arguments={"path": "data/missing.txt"})],
            )

    result = run_agent("读取缺失文件", workspace, RepeatLLM(), max_steps=8)
    assert result.status == "cannot_continue"
    assert result.steps == 2
    assert "连续失败 2 次" in result.answer
    assert "文件不存在" in result.answer


def test_step_limit_stops_successful_retries(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    class AlwaysCalculate:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del messages, tools
            return Decision(
                thought="继续计算",
                tool_calls=[ToolCall(name="calculator", arguments={"expression": "1+1"})],
            )

    result = run_agent("一直计算", workspace, AlwaysCalculate(), max_steps=2)
    assert result.status == "step_limit"
    assert "最大轮数 2" in result.answer


def test_long_tool_output_is_truncated(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "big.txt").write_text("x" * 100, encoding="utf-8")

    class ReadThenAnswer:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            tool_messages = [message for message in messages if message.role == "tool"]
            if not tool_messages:
                return Decision(
                    thought="读取大文件",
                    tool_calls=[ToolCall(name="read_file", arguments={"path": "big.txt"})],
                )
            return Decision(thought="转述工具结果", final_answer=tool_messages[-1].content)

    result = run_agent("读取大文件", workspace, ReadThenAnswer(), output_limit=20)
    assert result.status == "final"
    assert result.answer.endswith("已截断")
    assert len(result.answer) < 100
