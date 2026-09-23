# 阶段门禁

进入下一阶段前，当前阶段的每一条都要成立。

## 阶段 0

- `docs/DESIGN.md` 写有 Loop、Tool、结束条件、无限调用、失败处理、四层职责、最大限制。
- `docs/DECISIONS.md` 写有「明确不做」。
- 仓库中还没有 `mini_agent/`。

## 阶段 1

- 连续两次运行 `python scripts/generate_workspace.py`，workspace 源文件内容不变。
- 存在 TODO、FIXME、普通代码、`sales.txt` 数字、说明文字。
- 不存在 `workspace/data/missing.txt`。
- 材料中能找到 `../secret.txt` 和 `2+`。
- `pytest tests/test_workspace.py` 通过。

## 阶段 2

- `pytest tests/test_tools.py` 通过。
- 测试覆盖成功读取、文件不存在、路径越界、非法表达式、空搜索、未知工具。
- 此阶段没有主循环，也没有 LLM 调用。

## 阶段 3

- `pytest tests/test_mock.py` 通过。
- 测试断言的是下一步工具名和参数，不是整段最终答案碰运气匹配。
- 销售额合计来自后续计算器结果，Mock 源码中不写死合计数字。

## 阶段 4

- `pytest tests/test_loop.py` 通过。
- 有一条「搜索后写入」的多轮路径。
- 有一条「同一失败调用两次后停止」的路径。
- Markdown Trace 含有 `User`、`Agent Decision`、`Tool Call`、`Tool Result`、`Final Answer`。

## 阶段 5

- `pytest tests/test_openai_adapter.py` 通过，且测试不打开外部网络。
- 畸形响应变成可处理错误。
- 无密钥时计划书写「适配器已测，实跑待密钥」。

## 阶段 6

- `python scripts/run_tasks.py --llm mock` 通过。
- `todo-report.md` 按文件列出 TODO。
- `report.md` 中的合计等于计算器对当前 `sales.txt` 的结果。
- `summary.md` 同时含缺失文件错误、FIXME 和销售额。
- 越界任务的最终答案含失败原因。
- `docs/traces/` 中至少一份 Trace 顺序完整。

## 阶段 7

- `pytest` 全部通过。
- README 能让人从生成 workspace 跑到 Trace。
- 真实模型要么有独立 Trace 目录，要么文档明确写未实跑。
- 交付清单和基础能力清单已勾选。
- `AI_USAGE.md` 含参与环节、候选人决定、错误判断和修正。
