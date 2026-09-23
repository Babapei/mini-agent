"""把文件路径限制在 workspace 根目录之内。"""

from __future__ import annotations

from pathlib import Path

from mini_agent.tools.base import ToolError


def resolve_inside(workspace: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ToolError("路径为空")
    root = workspace.resolve()
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ToolError(f"路径超出 workspace：{raw}")
    return resolved
