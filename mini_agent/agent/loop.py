"""根据模型决策调用工具，直到结束、轮数耗尽或无法继续。"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mini_agent.llm.base import LLMError, Message
from mini_agent.tools.base import ToolResult
from mini_agent.tools.registry import ToolRegistry
from mini_agent.trace.recorder import TraceRecorder

DEFAULT_MAX_STEPS = 12
DEFAULT_OUTPUT_LIMIT = 8000
DEFAULT_CONTEXT_LIMIT = 24000
COMPRESSED_PREFIX = "已压缩："
DEFAULT_SYSTEM_PROMPT = (
    "你是 Mini Agent。只通过工具读取文件、搜索文本、计算和写入文件。"
    "算术必须交给 calculator。路径必须留在 workspace 内。"
    "任务完成或无法继续时，直接给出最终答案，不要再调用工具。"
)


@dataclass(frozen=True)
class AgentEvent:
    kind: str
    name: str = ""
    text: str = ""


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
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
    allowed: set[str] | None = None,
    on_event: Callable[[AgentEvent], None] | None = None,
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
        compressed = compress_context(messages, context_limit)
        if compressed:
            recorder.compressed(compressed)
        try:
            decision = llm.decide(messages, registry.schemas())
        except LLMError as exc:
            return _finish(recorder, trace_dir, "cannot_continue", f"无法继续：模型响应不可用：{exc}", step - 1, on_event)
        except Exception as exc:
            return _finish(recorder, trace_dir, "cannot_continue", f"无法继续：模型决策失败：{exc}", step - 1, on_event)

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
                _emit(on_event, AgentEvent(kind="tool_call", name=call.name))
                result = registry.execute(call.name, call.arguments)
                shown = _limit_result(result, output_limit)
                recorder.tool_result(shown)
                _emit(on_event, AgentEvent(kind="tool_result", name=call.name, text=shown.text))
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
                if (
                    streak == 1
                    and call.name == "read_file"
                    and "文件不存在" in shown.text
                    and "路径超出" not in shown.text
                ):
                    hint = "恢复提示：文件不存在。可以用 search_text 按文件名查找，不要用同一路径再读一次。"
                    messages.append(Message(role="user", content=hint))
                    recorder.recovery_hint(hint)
                if streak >= 2:
                    answer = (
                        "无法继续：同一工具和参数连续失败 2 次。"
                        f"工具 {call.name}，参数 {signature[1]}。"
                        f"错误：{shown.text}"
                    )
                    return _finish(recorder, trace_dir, "cannot_continue", answer, step, on_event)
            last_tool_failed = round_failed
            continue
        if decision.final_answer:
            return _finish(recorder, trace_dir, "final", decision.final_answer, step, on_event)
        return _finish(recorder, trace_dir, "cannot_continue", "无法继续：模型没有给出工具调用或最终答案。", step, on_event)

    return _finish(recorder, trace_dir, "step_limit", f"无法继续：已达到最大轮数 {max_steps}。", max_steps, on_event)


def compress_context(messages: list[Message], limit: int) -> int:
    """超过总长度时，把最近一条之外的工具结果收成一行。不调用模型。"""
    if sum(len(message.content) for message in messages) <= limit:
        return 0
    tool_indexes = [index for index, message in enumerate(messages) if message.role == "tool"]
    if len(tool_indexes) < 2:
        return 0
    count = 0
    for index in tool_indexes[:-1]:
        message = messages[index]
        if message.content.startswith(COMPRESSED_PREFIX):
            continue
        first = ""
        for line in message.content.splitlines():
            if line.strip():
                first = line.strip()
                break
        if len(first) > 80:
            first = first[:80]
        status = "成功" if message.ok else "失败"
        name = message.name or "tool"
        message.content = f"{COMPRESSED_PREFIX}{name} {status}：{first}"
        count += 1
    return count


def _limit_result(result: ToolResult, limit: int) -> ToolResult:
    text = result.text
    if len(text) <= limit:
        return result
    clipped = text[:limit] + "\n已截断"
    if result.ok:
        return ToolResult(ok=True, output=clipped)
    return ToolResult(ok=False, error=clipped)


def _emit(on_event: Callable[[AgentEvent], None] | None, event: AgentEvent) -> None:
    if on_event is not None:
        on_event(event)


def _finish(
    recorder: TraceRecorder,
    trace_dir: Path | None,
    status: str,
    answer: str,
    steps: int,
    on_event: Callable[[AgentEvent], None] | None = None,
) -> AgentResult:
    recorder.final(status, answer)
    _emit(on_event, AgentEvent(kind="final", text=answer))
    if trace_dir is not None:
        recorder.write(trace_dir)
    return AgentResult(status=status, answer=answer, steps=steps, trace_markdown=recorder.markdown())
