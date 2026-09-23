"""OpenAI 兼容的 chat completions 工具调用。"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mini_agent.llm.base import Decision, LLMError, Message, ToolCall

_Opener = Callable[..., object]


class OpenAICompatibleLLM:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        timeout: float = 30,
        max_retries: int = 2,
        opener: _Opener | None = None,
    ) -> None:
        if not api_key or not base_url or not model:
            raise LLMError("缺少 OPENAI_API_KEY、OPENAI_BASE_URL 或 OPENAI_MODEL")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._opener = opener or urlopen

    @classmethod
    def from_env(cls) -> OpenAICompatibleLLM:
        values = {
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
            "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", ""),
            "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise LLMError("缺少环境变量：" + "、".join(missing))
        return cls(values["OPENAI_API_KEY"], values["OPENAI_BASE_URL"], values["OPENAI_MODEL"])

    def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [_message_payload(message) for message in messages],
            "tools": [_tool_payload(tool) for tool in tools],
        }
        raw = self._post(payload)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMError("模型响应不是 JSON") from exc
        return _decision_from_payload(data)

    def _post(self, payload: dict) -> str:
        request = Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        attempts = self.max_retries + 1
        last_error = "请求失败"
        for attempt in range(attempts):
            try:
                with self._opener(request, timeout=self.timeout) as response:
                    return response.read().decode("utf-8")
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {exc.code}: {detail}"
                if exc.code < 500 or attempt == attempts - 1:
                    raise LLMError(last_error) from exc
            except (URLError, TimeoutError) as exc:
                last_error = str(exc.reason if isinstance(exc, URLError) else exc)
                if attempt == attempts - 1:
                    raise LLMError(f"网络错误：{last_error}") from exc
        raise LLMError(last_error)


def _message_payload(message: Message) -> dict:
    if message.role == "tool":
        return {
            "role": "tool",
            "content": message.content,
            "tool_call_id": message.tool_call_id or "",
            "name": message.name or "",
        }
    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in message.tool_calls
            ],
        }
    return {"role": message.role, "content": message.content}


def _tool_payload(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
        },
    }


def _decision_from_payload(data: object) -> Decision:
    if not isinstance(data, dict):
        raise LLMError("模型响应格式不正确")
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LLMError("模型响应缺少 choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LLMError("模型响应缺少 message")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    raw_calls = message.get("tool_calls") or []
    if raw_calls:
        if not isinstance(raw_calls, list):
            raise LLMError("tool_calls 格式不正确")
        calls = [_parse_tool_call(item) for item in raw_calls]
        content = message.get("content") if isinstance(message.get("content"), str) else ""
        plan = content.strip() or None
        return Decision(thought=plan or "调用工具", tool_calls=calls, usage=usage, plan=plan)
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError("模型响应缺少最终答案")
    return Decision(thought=content, tool_calls=[], final_answer=content, usage=usage)


def _parse_tool_call(item: object) -> ToolCall:
    if not isinstance(item, dict):
        raise LLMError("工具调用无法解析")
    function = item.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        raise LLMError("工具调用无法解析")
    raw_arguments = function.get("arguments", "{}")
    try:
        if isinstance(raw_arguments, str):
            arguments = json.loads(raw_arguments or "{}")
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            raise LLMError("工具参数格式不正确")
    except json.JSONDecodeError as exc:
        raise LLMError("工具调用无法解析") from exc
    if not isinstance(arguments, dict):
        raise LLMError("工具参数必须是对象")
    call_id = item.get("id")
    return ToolCall(name=function["name"], arguments=arguments, id=str(call_id or ""))
