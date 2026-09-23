"""按名称注册并调用工具。"""

from __future__ import annotations

from pathlib import Path

from mini_agent.tools.base import ALL_PERMISSIONS, Handler, Tool, ToolError, ToolResult, validate_arguments
from mini_agent.tools.delegate import make_delegate
from mini_agent.tools.calculator import CALCULATOR
from mini_agent.tools.read_file import READ_FILE
from mini_agent.tools.search_text import SEARCH_TEXT
from mini_agent.tools.tool_search import TOOL_SEARCH
from mini_agent.tools.write_file import WRITE_FILE


class ToolRegistry:
    def __init__(
        self,
        workspace: Path,
        allowed: set[str] | None = None,
        *,
        enable_delegate: bool = False,
        delegate_handler: Handler | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.allowed = set(ALL_PERMISSIONS if allowed is None else allowed)
        tools = [READ_FILE, WRITE_FILE, SEARCH_TEXT, CALCULATOR, TOOL_SEARCH]
        if enable_delegate:
            if delegate_handler is None:
                raise ValueError("打开 delegate 时必须提供处理函数")
            tools.append(make_delegate(delegate_handler))
        self._tools: dict[str, Tool] = {tool.name: tool for tool in tools}

    def schemas(self) -> list[dict]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict | None) -> ToolResult:
        if not isinstance(arguments, dict):
            return ToolResult(ok=False, error="参数必须是对象")
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"未知工具：{name}")
        if tool.permission not in self.allowed:
            return ToolResult(ok=False, error=f"权限不足：{name} 需要 {tool.permission}")
        error = validate_arguments(tool.parameters, arguments)
        if error:
            return ToolResult(ok=False, error=error)
        try:
            output = tool.handler(self.workspace, arguments)
        except ToolError as exc:
            return ToolResult(ok=False, error=str(exc))
        except Exception as exc:
            return ToolResult(ok=False, error=f"工具执行异常：{exc}")
        return ToolResult(ok=True, output=output)
