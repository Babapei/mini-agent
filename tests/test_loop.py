import re
from pathlib import Path

from mini_agent.agent.loop import run_agent
from mini_agent.llm.base import Decision, Message, ToolCall
from mini_agent.tools.base import READ
from mini_agent.llm.mock import MockLLM
from mini_agent.tasks import RECOVERY_TASK, SALES_TASK, TODO_TASK
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
    assert headings.index("Plan") < headings.index("Tool Call")
    plan_text = result.trace_markdown.split("## Plan", 1)[1].split("##", 1)[0]
    assert "101" not in plan_text
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


def test_recovery_updates_plan_after_missing_file(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    result = run_agent(RECOVERY_TASK, workspace, MockLLM())
    headings = _headings(result.trace_markdown)
    update_at = headings.index("Plan Update")
    assert headings.index("Tool Result") < update_at
    assert "Tool Call" in headings[update_at + 1 :]
    assert "改为搜索 FIXME" in result.trace_markdown
    assert "101" not in result.trace_markdown.split("## Plan Update", 1)[1].split("##", 1)[0]


def test_sales_success_has_no_plan_update(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    result = run_agent(SALES_TASK, workspace, MockLLM())
    assert "Plan Update" not in _headings(result.trace_markdown)


def test_compression_keeps_the_latest_tool_result(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    body = "全文标记-" + ("x" * 300)
    (workspace / "big.txt").write_text(body, encoding="utf-8")

    class RepeatRead:
        def __init__(self) -> None:
            self.calls: list[list[Message]] = []

        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            self.calls.append(list(messages))
            tool_messages = [message for message in messages if message.role == "tool"]
            if len(tool_messages) >= 2:
                return Decision(thought="结束", final_answer="结束")
            return Decision(
                thought="再读",
                tool_calls=[ToolCall(name="read_file", arguments={"path": "big.txt"})],
            )

    llm = RepeatRead()
    result = run_agent("读两次", workspace, llm, context_limit=200)
    tool_messages = [message for message in llm.calls[-1] if message.role == "tool"]
    assert tool_messages[-1].content == body
    assert tool_messages[0].content.startswith("已压缩：read_file 成功：")
    assert "压缩了 1 条" in result.trace_markdown


def test_short_sales_task_is_not_compressed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)

    class Watching(MockLLM):
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            self.calls.append([message.content for message in messages])
            return super().decide(messages, tools)

    llm = Watching()
    result = run_agent(SALES_TASK, workspace, llm)
    assert all("已压缩" not in content for call in llm.calls for content in call)
    assert "Context Compression" not in result.trace_markdown


def test_callback_sees_search_before_final_answer(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    events = []
    result = run_agent(TODO_TASK, workspace, MockLLM(), on_event=events.append)
    kinds = [(event.kind, event.name) for event in events]
    assert kinds[0] == ("tool_call", "search_text")
    assert kinds[-1][0] == "final"
    assert result.answer
    assert events[-1].text == result.answer


def test_no_stream_prints_only_the_final_answer(tmp_path: Path, capsys) -> None:
    from mini_agent.cli import main

    workspace = tmp_path / "workspace"
    generate(workspace)
    code = main(
        [
            "run",
            TODO_TASK,
            "--workspace",
            str(workspace),
            "--llm",
            "mock",
            "--no-stream",
            "--trace-dir",
            str(tmp_path / "trace"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "tool:" not in captured.out
    assert "todo-report.md" in captured.out


def test_stream_prints_tool_name_before_answer(tmp_path: Path, capsys) -> None:
    from mini_agent.cli import main

    workspace = tmp_path / "workspace"
    generate(workspace)
    code = main(
        [
            "run",
            TODO_TASK,
            "--workspace",
            str(workspace),
            "--llm",
            "mock",
            "--trace-dir",
            str(tmp_path / "trace"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.index("tool: search_text") < captured.out.index("todo-report.md")


def test_missing_file_hint_is_visible_and_does_not_search(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    seen: list[list[Message]] = []

    class ReadMissing:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            seen.append(list(messages))
            if any(message.role == "tool" for message in messages):
                return Decision(thought="停止", final_answer="看到恢复提示")
            return Decision(
                thought="读取",
                tool_calls=[ToolCall(name="read_file", arguments={"path": "data/missing.txt"})],
            )

    result = run_agent("读取缺失文件", workspace, ReadMissing())
    assert any("恢复提示" in message.content for message in seen[-1])
    headings = _headings(result.trace_markdown)
    assert headings.count("Tool Call") == 1
    assert "read_file" in result.trace_markdown
    assert "Recovery Hint" in result.trace_markdown


def test_recovery_hint_follows_every_tool_result_in_the_same_turn(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("FIXME: 这里\n", encoding="utf-8")
    seen: list[list[Message]] = []

    class TwoCalls:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            seen.append(list(messages))
            if any(message.role == "tool" for message in messages):
                return Decision(thought="停止", final_answer="下一轮")
            return Decision(
                thought="同时读取和搜索",
                tool_calls=[
                    ToolCall(name="read_file", arguments={"path": "data/missing.txt"}, id="call-read"),
                    ToolCall(name="search_text", arguments={"query": "FIXME"}, id="call-search"),
                ],
            )

    result = run_agent("同时调用", workspace, TwoCalls())
    roles = [message.role for message in seen[-1]]
    assert roles[roles.index("assistant") + 1 : roles.index("assistant") + 3] == ["tool", "tool"]
    assert seen[-1][-1].role == "user"
    assert "恢复提示" in seen[-1][-1].content
    headings = _headings(result.trace_markdown)
    hint_at = headings.index("Recovery Hint")
    assert headings[:hint_at].count("Tool Result") == 2


def test_path_escape_does_not_add_recovery_hint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    seen: list[list[Message]] = []

    class ReadOutside:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            seen.append(list(messages))
            if any(message.role == "tool" for message in messages):
                return Decision(thought="停止", final_answer="越界")
            return Decision(
                thought="读取",
                tool_calls=[ToolCall(name="read_file", arguments={"path": "../secret.txt"})],
            )

    result = run_agent("读取越界文件", workspace, ReadOutside())
    assert all("恢复提示" not in message.content for message in seen[-1])
    assert "Recovery Hint" not in result.trace_markdown


def test_delegate_is_absent_for_the_default_todo_task(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)

    class Watching(MockLLM):
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            assert "delegate" not in {tool["name"] for tool in tools}
            return super().decide(messages, tools)

    result = run_agent(TODO_TASK, workspace, Watching())
    assert result.status == "final"


def test_delegate_runs_one_child_level(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    child_tool_names: list[set[str]] = []

    class Split:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            names = {tool["name"] for tool in tools}
            tool_messages = [message for message in messages if message.role == "tool"]
            if "delegate" not in names:
                child_tool_names.append(names)
                if tool_messages:
                    return Decision(thought="结束", final_answer=tool_messages[-1].content.strip())
                return Decision(
                    thought="计算",
                    tool_calls=[ToolCall(name="calculator", arguments={"expression": "1+1"})],
                )
            if not tool_messages:
                return Decision(
                    thought="委托",
                    tool_calls=[ToolCall(name="delegate", arguments={"task": "计算 1+1"})],
                )
            if tool_messages[-1].name == "delegate":
                return Decision(
                    thought="写入",
                    tool_calls=[
                        ToolCall(
                            name="write_file",
                            arguments={"path": "out.md", "content": tool_messages[-1].content},
                        )
                    ],
                )
            return Decision(thought="完成", final_answer="已写入")

    result = run_agent(
        "交给子任务",
        workspace,
        Split(),
        trace_dir=tmp_path / "trace",
        enable_delegate=True,
    )
    written = (workspace / "out.md").read_text(encoding="utf-8")
    assert result.status == "final"
    assert written.startswith("2\n")
    assert "子循环轮数：" in written
    assert child_tool_names
    assert all("delegate" not in names for names in child_tool_names)
    assert (tmp_path / "trace" / "sub" / "trace.md").is_file()
    assert "delegate" in result.trace_markdown


def test_failed_child_returns_to_parent_once(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    class AlwaysCalculate:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            names = {tool["name"] for tool in tools}
            tool_messages = [message for message in messages if message.role == "tool"]
            if "delegate" in names:
                if tool_messages:
                    assert tool_messages[-1].ok is False
                    return Decision(thought="停止", final_answer="子任务失败")
                return Decision(
                    thought="委托",
                    tool_calls=[ToolCall(name="delegate", arguments={"task": "一直计算"})],
                )
            return Decision(
                thought="继续",
                tool_calls=[ToolCall(name="calculator", arguments={"expression": "1+1"})],
            )

    result = run_agent("父任务", workspace, AlwaysCalculate(), enable_delegate=True, sub_max_steps=1)
    assert result.status == "final"
    assert result.answer == "子任务失败"
    assert _headings(result.trace_markdown).count("Tool Call") == 1


def test_read_only_run_records_write_denial(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    class WriteOnce:
        def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
            del tools
            if any(message.role == "tool" for message in messages):
                return Decision(thought="停止", final_answer="写入被拒绝")
            return Decision(
                thought="尝试写入",
                tool_calls=[ToolCall(name="write_file", arguments={"path": "out.md", "content": "nope"})],
            )

    result = run_agent("只读写入", workspace, WriteOnce(), allowed={READ})
    assert result.status == "final"
    assert "权限不足：write_file 需要 write" in result.trace_markdown
    assert not (workspace / "out.md").exists()
