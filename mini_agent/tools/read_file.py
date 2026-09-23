"""读取 workspace 内的文本文件。"""

from __future__ import annotations

from pathlib import Path

from mini_agent.tools.base import Tool, ToolError
from mini_agent.tools.sandbox import resolve_inside


def read_file(workspace: Path, arguments: dict) -> str:
    raw = arguments["path"]
    path = resolve_inside(workspace, raw)
    if not path.exists():
        raise ToolError(f"文件不存在：{raw}")
    if not path.is_file():
        raise ToolError(f"不是文件：{raw}")
    return path.read_text(encoding="utf-8")


READ_FILE = Tool(
    name="read_file",
    description="读取 workspace 内的文本文件。path 是相对 workspace 的路径。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "workspace 内的相对路径"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    handler=read_file,
    permission="read",
)
