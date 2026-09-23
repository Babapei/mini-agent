from pathlib import Path

from scripts.generate_workspace import FILES, generate


def _snapshot(dest: Path) -> dict[str, str]:
    return {
        path.relative_to(dest).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(dest.rglob("*"))
        if path.is_file()
    }


def test_generate_twice_is_stable(tmp_path: Path) -> None:
    dest = tmp_path / "workspace"
    generate(dest)
    first = _snapshot(dest)
    generate(dest)
    assert _snapshot(dest) == first


def test_workspace_contains_required_categories(tmp_path: Path) -> None:
    dest = tmp_path / "workspace"
    generate(dest)

    readme = (dest / "README.md").read_text(encoding="utf-8")
    user_code = (dest / "src" / "user.ts").read_text(encoding="utf-8")
    order_code = (dest / "src" / "order.ts").read_text(encoding="utf-8")
    design = (dest / "docs" / "design.md").read_text(encoding="utf-8")
    sales = (dest / "data" / "sales.txt").read_text(encoding="utf-8").splitlines()
    bad_expr = (dest / "data" / "bad_expr.txt").read_text(encoding="utf-8")

    assert "TODO" in readme
    assert "data/missing.txt" in readme
    assert "../secret.txt" in readme
    assert "说明" in readme
    assert "TODO" in user_code
    assert "export function" in user_code
    assert "FIXME" in order_code
    assert "TODO" in design and "FIXME" in design
    assert sales[0] == "product,quantity,price"
    assert len(sales) >= 2
    assert bad_expr.strip() == "2+"
    assert not (dest / "data" / "missing.txt").exists()
    assert set(FILES) == set(_snapshot(dest))
