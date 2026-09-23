"""只计算数字和四则运算，不执行任意代码。"""

from __future__ import annotations

import ast
import math
import operator
from pathlib import Path

from mini_agent.tools.base import Tool, ToolError

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_MAX_EXPONENT = 20


def calculator(workspace: Path, arguments: dict) -> str:
    del workspace
    expression = arguments["expression"].strip()
    if not expression:
        raise ToolError("表达式为空")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"非法表达式：{exc.msg}") from exc
    try:
        value = _evaluate(tree)
    except ToolError:
        raise
    except ZeroDivisionError as exc:
        raise ToolError("除数不能为 0") from exc
    return _format_number(value)


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError("非法表达式：只允许数字")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ToolError("指数过大")
        return _BINARY[type(node.op)](left, right)
    raise ToolError("非法表达式")


def _format_number(value: int | float) -> str:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ToolError("结果不是有限数字")
        if value.is_integer():
            return str(int(value))
        text = format(value, ".12g")
        return text
    return str(value)


CALCULATOR = Tool(
    name="calculator",
    description="计算只含数字、括号和 + - * / // % ** 的表达式。",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "算术表达式"},
        },
        "required": ["expression"],
        "additionalProperties": False,
    },
    handler=calculator,
    permission="compute",
)
