"""把文本写入 workspace 内的文件。"""

from __future__ import annotations

from pathlib import Path

from mini_agent.tools.base import Tool, ToolError
from mini_agent.tools.sandbox import resolve_inside


def write_file(workspace: Path, arguments: dict) -> str:
    raw = arguments["path"]
    path = resolve_inside(workspace, raw)
    if path.exists() and not path.is_file():
        raise ToolError(f"不是文件：{raw}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(arguments["content"], encoding="utf-8")
    return f"已写入 {raw}"


WRITE_FILE = Tool(
    name="write_file",
    description="把 content 写入 workspace 内的 path。父目录不存在时会创建。",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "workspace 内的相对路径"},
            "content": {"type": "string", "description": "要写入的文本"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
    handler=write_file,
    permission="write",
)
