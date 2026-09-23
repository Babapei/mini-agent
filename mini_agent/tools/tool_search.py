"""按字面量查找已注册工具的名称和说明。"""

from __future__ import annotations

from pathlib import Path

from mini_agent.tools.base import Tool, ToolError
from mini_agent.tools.calculator import CALCULATOR
from mini_agent.tools.read_file import READ_FILE
from mini_agent.tools.search_text import SEARCH_TEXT
from mini_agent.tools.write_file import WRITE_FILE


def tool_search(workspace: Path, arguments: dict) -> str:
    del workspace
    query = arguments["query"].strip()
    if not query:
        raise ToolError("查询不能为空")
    lines = [
        f"{tool.name}：{tool.description}"
        for tool in _catalog()
        if query in tool.name or query in tool.description
    ]
    return "\n".join(lines)


def _catalog() -> tuple[Tool, ...]:
    return (READ_FILE, WRITE_FILE, SEARCH_TEXT, CALCULATOR, TOOL_SEARCH)


TOOL_SEARCH = Tool(
    name="tool_search",
    description="按字面量查找已有工具的名称和说明。query 是要查找的文字。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "要在工具名或说明里查找的文字"},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    handler=tool_search,
    permission="read",
)
