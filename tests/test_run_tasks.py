from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.generate_workspace import generate
from scripts.run_tasks import _check, main


def test_missing_openai_credentials_do_not_change_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = tmp_path / "workspace"
    generate(workspace)
    report = workspace / "report.md"
    report.write_text("keep", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    code = main(
        [
            "--llm",
            "openai",
            "--workspace",
            str(workspace),
            "--trace-root",
            str(tmp_path / "traces"),
        ]
    )

    assert code == 2
    assert report.read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / "traces").exists()


def test_mock_wording_check_rejects_a_refusal_without_tool_call() -> None:
    result = SimpleNamespace(
        status="final",
        answer="不能读取 workspace 之外的文件。",
        trace_markdown="# Agent Trace\n\n## User\n\n越界\n\n## Agent Decision\n\n拒绝\n\n## Final Answer\n\n不能读取\n",
    )
    task = {"id": "04-blocked", "kind": "blocked", "prompt": "", "output": None}

    problems = _check(task, Path("."), result)

    assert any("Tool Call" in problem for problem in problems)
