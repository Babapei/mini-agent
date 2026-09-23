from pathlib import Path

import pytest

from scripts.generate_workspace import generate
from scripts.run_tasks import main


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
