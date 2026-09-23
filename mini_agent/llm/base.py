"""循环和模型之间的消息与决策。"""

from __future__ import annotations

from dataclasses import dataclass, field


class LLMError(Exception):
    """模型响应不可用，或调用模型所需的配置缺失。"""


@dataclass
class ToolCall:
    name: str
    arguments: dict
    id: str = ""


@dataclass
class Decision:
    thought: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    final_answer: str | None = None
    usage: dict | None = None


@dataclass
class Message:
    role: str
    content: str
    name: str | None = None
    ok: bool | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None
