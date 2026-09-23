"""根据模型决策调用工具，直到结束、轮数耗尽或无法继续。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mini_agent.llm.base import LLMError, Message
from mini_agent.tools.base import ToolResult
from mini_agent.tools.registry import ToolRegistry
from mini_agent.trace.recorder import TraceRecorder

DEFAULT_MAX_STEPS = 12
DEFAULT_OUTPUT_LIMIT = 8000
DEFAULT_SYSTEM_PROMPT = (
    "你是 Mini Agent。只通过工具读取文件、搜索文本、计算和写入文件。"
    "算术必须交给 calculator。路径必须留在 workspace 内。"
    "任务完成或无法继续时，直接给出最终答案，不要再调用工具。"
)


@dataclass
class AgentResult:
    status: str
    answer: str
    steps: int
    trace_markdown: str


def run_agent(
    task: str,
    workspace: Path,
    llm,
    *,
    max_steps: int = DEFAULT_MAX_STEPS,
    trace_dir: Path | None = None,
    system_prompt: str | None = None,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
    allowed: set[str] | None = None,
) -> AgentResult:
    registry = ToolRegistry(workspace, allowed)
    recorder = TraceRecorder()
    recorder.user(task)
    messages = [
        Message(role="system", content=system_prompt or DEFAULT_SYSTEM_PROMPT),
        Message(role="user", content=task),
    ]
    last_signature: tuple[str, str] | None = None
    streak = 0
    planned = False
    last_tool_failed = False

    for step in range(1, max_steps + 1):
        try:
            decision = llm.decide(messages, registry.schemas())
        except LLMError as exc:
            return _finish(recorder, trace_dir, "cannot_continue", f"无法继续：模型响应不可用：{exc}", step - 1)
        except Exception as exc:
            return _finish(recorder, trace_dir, "cannot_continue", f"无法继续：模型决策失败：{exc}", step - 1)

        if decision.tool_calls and not planned and decision.plan:
            recorder.plan(decision.plan)
            planned = True
        if decision.plan_update and last_tool_failed:
            recorder.plan_update(decision.plan_update)
        recorder.decision(step, decision)
        if decision.tool_calls:
            messages.append(Message(role="assistant", content=decision.thought, tool_calls=list(decision.tool_calls)))
            round_failed = False
            for index, call in enumerate(decision.tool_calls, start=1):
                if not call.id:
                    call.id = f"call-{step}-{index}"
                recorder.tool_call(call)
                result = registry.execute(call.name, call.arguments)
                shown = _limit_result(result, output_limit)
                recorder.tool_result(shown)
                messages.append(
                    Message(
                        role="tool",
                        content=shown.text,
                        name=call.name,
                        ok=shown.ok,
                        tool_call_id=call.id,
                    )
                )
                round_failed = not shown.ok
                if shown.ok:
                    last_signature = None
                    streak = 0
                    continue
                signature = (
                    call.name,
                    json.dumps(call.arguments, ensure_ascii=False, sort_keys=True),
                )
                if signature == last_signature:
                    streak += 1
                else:
                    last_signature = signature
                    streak = 1
                if streak >= 2:
                    answer = (
                        "无法继续：同一工具和参数连续失败 2 次。"
                        f"工具 {call.name}，参数 {signature[1]}。"
                        f"错误：{shown.text}"
                    )
                    return _finish(recorder, trace_dir, "cannot_continue", answer, step)
            last_tool_failed = round_failed
            continue
        if decision.final_answer:
            return _finish(recorder, trace_dir, "final", decision.final_answer, step)
        return _finish(recorder, trace_dir, "cannot_continue", "无法继续：模型没有给出工具调用或最终答案。", step)

    return _finish(recorder, trace_dir, "step_limit", f"无法继续：已达到最大轮数 {max_steps}。", max_steps)


def _limit_result(result: ToolResult, limit: int) -> ToolResult:
    text = result.text
    if len(text) <= limit:
        return result
    clipped = text[:limit] + "\n已截断"
    if result.ok:
        return ToolResult(ok=True, output=clipped)
    return ToolResult(ok=False, error=clipped)


def _finish(
    recorder: TraceRecorder,
    trace_dir: Path | None,
    status: str,
    answer: str,
    steps: int,
) -> AgentResult:
    recorder.final(status, answer)
    if trace_dir is not None:
        recorder.write(trace_dir)
    return AgentResult(status=status, answer=answer, steps=steps, trace_markdown=recorder.markdown())
