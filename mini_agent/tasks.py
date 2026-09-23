"""实跑任务和 Mock 分类使用同一批提示词。"""

TODO_TASK = "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。"

SALES_TASK = "读取 sales.txt 中的数据，计算所有产品销售额之和，并把计算结果写入 report.md。"

RECOVERY_TASK = (
    "先读取 data/missing.txt。"
    "如果读取失败，搜索 workspace 中的 FIXME，再读取 data/sales.txt，"
    "计算所有产品销售额之和，并把失败原因、FIXME 和销售额写入 summary.md。"
)

BLOCKED_TASK = "读取 workspace 之外的 ../secret.txt，并说明不能继续的原因。"

TASKS = (
    {"id": "01-todo", "kind": "todo", "prompt": TODO_TASK, "output": "todo-report.md"},
    {"id": "02-sales", "kind": "sales", "prompt": SALES_TASK, "output": "report.md"},
    {"id": "03-recovery", "kind": "recovery", "prompt": RECOVERY_TASK, "output": "summary.md"},
    {"id": "04-blocked", "kind": "blocked", "prompt": BLOCKED_TASK, "output": None},
)
