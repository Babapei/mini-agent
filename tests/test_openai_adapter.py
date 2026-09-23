from __future__ import annotations

import json
from email.message import EmailMessage
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from mini_agent.llm.base import LLMError, Message, ToolCall
from mini_agent.llm.openai_compatible import OpenAICompatibleLLM


class Response:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _llm(opener) -> OpenAICompatibleLLM:
    return OpenAICompatibleLLM(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        max_retries=2,
        opener=opener,
    )


def _tools() -> list[dict]:
    return [
        {
            "name": "read_file",
            "description": "读取文件",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        }
    ]


def test_parses_tool_call_and_sends_schema() -> None:
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["auth"] = request.get_header("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        payload = {
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\": \"data/sales.txt\"}",
                                },
                            }
                        ],
                    }
                }
            ],
        }
        return Response(json.dumps(payload))

    decision = _llm(opener).decide([Message(role="user", content="读取销售数据")], _tools())
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["tools"][0]["type"] == "function"
    assert captured["body"]["tools"][0]["function"]["name"] == "read_file"
    assert decision.tool_calls[0].name == "read_file"
    assert decision.tool_calls[0].arguments == {"path": "data/sales.txt"}
    assert decision.tool_calls[0].id == "call_1"
    assert decision.usage == {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}


def test_parses_final_answer() -> None:
    def opener(request, timeout):
        del request, timeout
        payload = {"choices": [{"message": {"role": "assistant", "content": "已完成"}}]}
        return Response(json.dumps(payload))

    decision = _llm(opener).decide([Message(role="user", content="任务")], [])
    assert decision.tool_calls == []
    assert decision.final_answer == "已完成"


def test_malformed_responses_raise_llm_error() -> None:
    def opener_for(body: str):
        def opener(request, timeout):
            del request, timeout
            return Response(body)

        return opener

    with pytest.raises(LLMError, match="不是 JSON"):
        _llm(opener_for("not-json")).decide([Message(role="user", content="任务")], [])
    with pytest.raises(LLMError, match="缺少 choices"):
        _llm(opener_for(json.dumps({"choices": []}))).decide([Message(role="user", content="任务")], [])
    broken_call = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {"id": "call_1", "function": {"name": "read_file", "arguments": "not-json"}}
                    ]
                }
            }
        ]
    }
    with pytest.raises(LLMError, match="无法解析"):
        _llm(opener_for(json.dumps(broken_call))).decide([Message(role="user", content="任务")], [])


def test_network_error_retries_then_succeeds() -> None:
    calls = {"count": 0}

    def opener(request, timeout):
        del request, timeout
        calls["count"] += 1
        if calls["count"] == 1:
            raise URLError("down")
        return Response(json.dumps({"choices": [{"message": {"content": "重试后完成"}}]}))

    decision = _llm(opener).decide([Message(role="user", content="任务")], [])
    assert calls["count"] == 2
    assert decision.final_answer == "重试后完成"


def test_client_error_does_not_retry() -> None:
    calls = {"count": 0}

    def opener(request, timeout):
        del timeout
        calls["count"] += 1
        raise HTTPError(request.full_url, 400, "bad", EmailMessage(), BytesIO(b"bad request"))

    with pytest.raises(LLMError, match="HTTP 400"):
        _llm(opener).decide([Message(role="user", content="任务")], [])
    assert calls["count"] == 1


def test_from_env_reports_missing_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        OpenAICompatibleLLM.from_env()


def test_assistant_tool_history_is_sent() -> None:
    captured = {}

    def opener(request, timeout):
        del timeout
        captured["messages"] = json.loads(request.data.decode("utf-8"))["messages"]
        return Response(json.dumps({"choices": [{"message": {"content": "好"}}]}))

    messages = [
        Message(
            role="assistant",
            content="读取",
            tool_calls=[ToolCall(name="read_file", arguments={"path": "a.txt"}, id="call-1")],
        ),
        Message(role="tool", content="文件不存在", name="read_file", ok=False, tool_call_id="call-1"),
    ]
    _llm(opener).decide(messages, _tools())
    assert captured["messages"][0]["tool_calls"][0]["id"] == "call-1"
    assert captured["messages"][1]["role"] == "tool"
    assert captured["messages"][1]["content"] == "文件不存在"
