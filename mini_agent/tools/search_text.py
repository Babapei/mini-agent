"""在 workspace 内按字面量搜索文本。"""

from __future__ import annotations

import os
from pathlib import Path

from mini_agent.tools.base import Tool, ToolError
from mini_agent.tools.sandbox import resolve_inside


def search_text(workspace: Path, arguments: dict) -> str:
    query = arguments["query"]
    if query == "":
        raise ToolError("搜索文本为空")
    raw_path = arguments.get("path") or "."
    base = resolve_inside(workspace, raw_path)
    if base.is_file():
        files = [base]
    elif base.is_dir():
        files = _list_files(base)
    else:
        raise ToolError(f"搜索路径不存在：{raw_path}")

    root = workspace.resolve()
    matches: list[str] = []
    for file in files:
        resolved = file.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            continue
        try:
            text = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = resolved.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if query in line:
                matches.append(f"{relative}:{lineno}:{line}")
    return "\n".join(matches)


def _list_files(base: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for name in filenames:
            files.append(Path(dirpath) / name)
    return files


SEARCH_TEXT = Tool(
    name="search_text",
    description="在 workspace 内搜索 query 的字面量，返回 文件:行号:内容。path 可省略，默认整个 workspace。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "要搜索的字面量"},
            "path": {"type": "string", "description": "可选，workspace 内的文件或目录"},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    handler=search_text,
)
