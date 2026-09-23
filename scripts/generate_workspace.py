"""生成 Mini Agent 的测试 workspace。重复运行会覆盖同一批源文件。"""

from __future__ import annotations

import argparse
from pathlib import Path

FILES = {
    "README.md": """# Workspace

本目录是 Mini Agent 的测试材料，里面有说明文字、待办和会失败的输入。

- TODO: 补充用户注册流程说明

设计文档提到了不存在的文件 data/missing.txt，用于失败恢复任务。

失败输入示例：路径 `../secret.txt`，非法算式 `2+`。
""",
    "src/user.ts": """export type User = { id: string; name: string };

export function formatUser(user: User): string {
  // TODO: 处理空名字
  return user.name.trim();
}
""",
    "src/order.ts": """export type Order = { id: string; amount: number };

export function total(orders: Order[]): number {
  // FIXME: 没有处理空数组
  return orders.reduce((sum, order) => sum + order.amount, 0);
}
""",
    "docs/design.md": """# 订单模块说明

订单金额由数量和单价相乘后累加。这里是普通的设计说明。

- TODO: 补充折扣规则
- FIXME: 运费未计入
""",
    "data/sales.txt": """product,quantity,price
Pen,2,10.5
Notebook,3,20
Paper,4,5
""",
    "data/bad_expr.txt": """2+
""",
}

GENERATED_OUTPUTS = ("todo-report.md", "report.md", "summary.md")


def generate(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for relative, content in FILES.items():
        path = dest / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    missing = dest / "data" / "missing.txt"
    if missing.exists():
        missing.unlink()
    for name in GENERATED_OUTPUTS:
        output = dest / name
        if output.exists():
            output.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成 Mini Agent 测试 workspace")
    parser.add_argument("--dest", default="workspace", help="输出目录，默认 workspace")
    args = parser.parse_args(argv)
    dest = Path(args.dest)
    generate(dest)
    print(f"已生成 {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
