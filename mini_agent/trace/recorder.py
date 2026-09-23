"""把一次任务记成 Markdown 和 JSONL。"""

from __future__ import annotations

import json
from pathlib import Path

from mini_agent.llm.base import Decision, ToolCall
from mini_agent.tools.base import ToolResult


class TraceRecorder:
    def __init__(self) -> None:
        self._lines = ["# Agent Trace", ""]
        self.events: list[dict] = []

    def user(self, text: str) -> None:
        self._section("User", text)
        self.events.append({"type": "user", "content": text})

    def decision(self, step: int, decision: Decision) -> None:
        body = [f"step: {step}", f"thought: {decision.thought}"]
        if decision.tool_calls:
            body.append("tool_calls:")
            for call in decision.tool_calls:
                body.append(
                    f"- {call.name} {json.dumps(call.arguments, ensure_ascii=False, sort_keys=True)}"
                )
        if decision.final_answer and not decision.tool_calls:
            body.append("final_answer:")
            body.append(decision.final_answer)
        if decision.usage:
            body.append("usage: " + json.dumps(decision.usage, ensure_ascii=False, sort_keys=True))
        self._section("Agent Decision", "\n".join(body))
        self.events.append(
            {
                "type": "agent_decision",
                "step": step,
                "thought": decision.thought,
                "tool_calls": [
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in decision.tool_calls
                ],
                "final_answer": decision.final_answer,
                "usage": decision.usage,
            }
        )

    def tool_call(self, call: ToolCall) -> None:
        body = f"{call.name}\n{json.dumps(call.arguments, ensure_ascii=False, sort_keys=True)}"
        self._section("Tool Call", body)
        self.events.append(
            {
                "type": "tool_call",
                "id": call.id,
                "name": call.name,
                "arguments": call.arguments,
            }
        )

    def tool_result(self, result: ToolResult) -> None:
        body = f"ok: {str(result.ok).lower()}\n{result.text}"
        self._section("Tool Result", body)
        self.events.append({"type": "tool_result", "ok": result.ok, "content": result.text})

    def final(self, status: str, answer: str) -> None:
        self._section("Final Answer", f"status: {status}\n{answer}")
        self.events.append({"type": "final", "status": status, "content": answer})

    def markdown(self) -> str:
        return "\n".join(self._lines).rstrip() + "\n"

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "trace.md").write_text(self.markdown(), encoding="utf-8")
        lines = [json.dumps(event, ensure_ascii=False) for event in self.events]
        (directory / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _section(self, title: str, body: str) -> None:
        self._lines.extend([f"## {title}", "", body.rstrip(), ""])
