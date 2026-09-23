from mini_agent.llm.base import Message
from mini_agent.llm.mock import MockLLM
from mini_agent.tasks import BLOCKED_TASK, RECOVERY_TASK, SALES_TASK, TODO_TASK


def _tool(name: str, content: str, ok: bool = True) -> Message:
    return Message(role="tool", content=content, name=name, ok=ok)


def test_todo_decisions_follow_search_result() -> None:
    llm = MockLLM()
    first = llm.decide([Message(role="user", content=TODO_TASK)], [])
    assert [call.name for call in first.tool_calls] == ["search_text"]
    assert first.tool_calls[0].arguments == {"query": "TODO"}

    second = llm.decide(
        [
            Message(role="user", content=TODO_TASK),
            _tool("search_text", "src/user.ts:4:// TODO: 处理空名字"),
        ],
        [],
    )
    assert second.tool_calls[0].name == "write_file"
    assert second.tool_calls[0].arguments["path"] == "todo-report.md"
    assert "## src/user.ts" in second.tool_calls[0].arguments["content"]
    assert "处理空名字" in second.tool_calls[0].arguments["content"]

    third = llm.decide(
        [
            Message(role="user", content=TODO_TASK),
            _tool("search_text", "src/user.ts:4:// TODO: 处理空名字"),
            _tool("write_file", "已写入 todo-report.md"),
        ],
        [],
    )
    assert third.tool_calls == []
    assert third.final_answer is not None
    assert "todo-report.md" in third.final_answer


def test_sales_total_comes_from_calculator_result() -> None:
    llm = MockLLM()
    csv_text = "product,quantity,price\nA,2,10\nB,4,5\n"
    first = llm.decide([Message(role="user", content=SALES_TASK)], [])
    assert first.tool_calls[0].arguments == {"path": "data/sales.txt"}

    second = llm.decide(
        [Message(role="user", content=SALES_TASK), _tool("read_file", csv_text)],
        [],
    )
    assert second.tool_calls[0].name == "calculator"
    assert second.tool_calls[0].arguments == {"expression": "2*10+4*5"}

    third = llm.decide(
        [
            Message(role="user", content=SALES_TASK),
            _tool("read_file", csv_text),
            _tool("calculator", "TOTAL-40"),
        ],
        [],
    )
    content = third.tool_calls[0].arguments["content"]
    assert "TOTAL-40" in content
    assert "2*10+4*5" in content
    assert third.tool_calls[0].arguments["path"] == "report.md"


def test_recovery_starts_with_missing_file() -> None:
    llm = MockLLM()
    first = llm.decide([Message(role="user", content=RECOVERY_TASK)], [])
    assert first.tool_calls[0].name == "read_file"
    assert first.tool_calls[0].arguments == {"path": "data/missing.txt"}

    second = llm.decide(
        [
            Message(role="user", content=RECOVERY_TASK),
            _tool("read_file", "文件不存在：data/missing.txt", ok=False),
        ],
        [],
    )
    assert second.tool_calls[0].name == "search_text"
    assert second.tool_calls[0].arguments == {"query": "FIXME"}


def test_blocked_and_unknown_tasks() -> None:
    llm = MockLLM()
    blocked = llm.decide([Message(role="user", content=BLOCKED_TASK)], [])
    assert blocked.tool_calls[0].arguments == {"path": "../secret.txt"}

    after_error = llm.decide(
        [
            Message(role="user", content=BLOCKED_TASK),
            _tool("read_file", "路径超出 workspace：../secret.txt", ok=False),
        ],
        [],
    )
    assert after_error.tool_calls == []
    assert after_error.final_answer is not None
    assert "路径超出 workspace" in after_error.final_answer

    illegal = llm.decide([Message(role="user", content="请计算非法算式 2+。")], [])
    assert illegal.tool_calls[0].name == "calculator"
    assert illegal.tool_calls[0].arguments == {"expression": "2+"}

    unknown = llm.decide([Message(role="user", content="帮我写一首诗")], [])
    assert unknown.tool_calls == []
    assert unknown.final_answer is not None
    assert "不能规划" in unknown.final_answer
