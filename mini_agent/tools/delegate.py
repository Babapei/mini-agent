"""把一句子任务交给下一层 Agent。"""

from __future__ import annotations

from mini_agent.tools.base import Handler, Tool


def make_delegate(handler: Handler) -> Tool:
    return Tool(
        name="delegate",
        description="把一句子任务交给下一层 Agent，并返回它的最终答案。子层不能再委托。",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "交给下一层的子任务"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
        handler=handler,
        permission="read",
    )
