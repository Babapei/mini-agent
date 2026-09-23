from pathlib import Path

from mini_agent.tools.base import READ
from mini_agent.tools.registry import ToolRegistry


def _registry(tmp_path: Path) -> ToolRegistry:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("alpha\nTODO: 写测试\n", encoding="utf-8")
    return ToolRegistry(workspace)


def test_read_file_returns_text(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    result = registry.execute("read_file", {"path": "notes.txt"})
    assert result.ok
    assert "TODO: 写测试" in result.output


def test_read_file_missing_is_a_result(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    result = registry.execute("read_file", {"path": "data/missing.txt"})
    assert not result.ok
    assert "文件不存在" in result.error


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    outside = tmp_path / "secret.txt"
    result = registry.execute("write_file", {"path": "../secret.txt", "content": "nope"})
    assert not result.ok
    assert "路径超出 workspace" in result.error
    assert not outside.exists()

    absolute = registry.execute("read_file", {"path": "/etc/passwd"})
    assert not absolute.ok
    assert "路径超出 workspace" in absolute.error


def test_symlink_outside_workspace_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "leak.txt").symlink_to(outside)
    registry = ToolRegistry(workspace)
    result = registry.execute("read_file", {"path": "leak.txt"})
    assert not result.ok
    assert "路径超出 workspace" in result.error


def test_search_text_format_and_empty_query(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    found = registry.execute("search_text", {"query": "TODO"})
    assert found.ok
    assert found.output == "notes.txt:2:TODO: 写测试"

    empty_hit = registry.execute("search_text", {"query": "不存在的句子"})
    assert empty_hit.ok
    assert empty_hit.output == ""

    empty_query = registry.execute("search_text", {"query": ""})
    assert not empty_query.ok
    assert "搜索文本为空" in empty_query.error


def test_calculator_arithmetic_and_rejection(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    assert registry.execute("calculator", {"expression": "1+2*3"}).output == "7"
    assert registry.execute("calculator", {"expression": "(1+2)*3"}).output == "9"
    assert registry.execute("calculator", {"expression": "2*10.5+3*20+4*5"}).output == "101"

    invalid = registry.execute("calculator", {"expression": "2+"})
    assert not invalid.ok
    assert "非法表达式" in invalid.error

    unsafe = registry.execute("calculator", {"expression": "__import__('os').system('ls')"})
    assert not unsafe.ok


def test_unknown_tool_and_bad_arguments_do_not_raise(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    unknown = registry.execute("missing_tool", {})
    assert not unknown.ok
    assert "未知工具" in unknown.error

    missing_arg = registry.execute("read_file", {})
    assert not missing_arg.ok
    assert "缺少参数" in missing_arg.error

    bad_type = registry.execute("read_file", {"path": 12})
    assert not bad_type.ok
    assert "参数类型错误" in bad_type.error

    extra = registry.execute("read_file", {"path": "notes.txt", "mode": "all"})
    assert not extra.ok
    assert "未知参数" in extra.error


def test_read_only_permission_blocks_write_but_allows_read_and_search(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("TODO: 写测试\n", encoding="utf-8")
    registry = ToolRegistry(workspace, allowed={READ})

    denied = registry.execute("write_file", {"path": "out.md", "content": "nope"})
    assert not denied.ok
    assert denied.error == "权限不足：write_file 需要 write"
    assert not (workspace / "out.md").exists()

    assert registry.execute("calculator", {"expression": "1+1"}).error == "权限不足：calculator 需要 compute"
    assert registry.execute("read_file", {"path": "notes.txt"}).ok
    found = registry.execute("search_text", {"query": "TODO"})
    assert found.ok
    assert "notes.txt:1:TODO: 写测试" in found.output


def test_allowed_write_still_rejects_path_escape(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    outside = tmp_path / "secret.txt"
    result = registry.execute("write_file", {"path": "../secret.txt", "content": "nope"})
    assert not result.ok
    assert "路径超出 workspace" in result.error
    assert "权限不足" not in result.error
    assert not outside.exists()
