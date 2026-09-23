"""工具规格、结果和参数校验。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class ToolError(Exception):
    """工具可预期的失败。调用方把它转换成失败结果。"""


@dataclass
class ToolResult:
    ok: bool
    output: str = ""
    error: str = ""

    @property
    def text(self) -> str:
        return self.output if self.ok else self.error


Handler = Callable[[Path, dict], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Handler

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


def validate_arguments(schema: dict, arguments: dict) -> str | None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for key in required:
        if key not in arguments:
            return f"缺少参数：{key}"
    for key, value in arguments.items():
        if key not in properties:
            return f"未知参数：{key}"
        expected = properties[key].get("type")
        if expected == "string" and not isinstance(value, str):
            return f"参数类型错误：{key} 应为字符串"
        if expected == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
            return f"参数类型错误：{key} 应为数字"
    return None
