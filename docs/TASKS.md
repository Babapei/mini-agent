# 测试任务

四个任务使用 `mini_agent/tasks.py` 里的同一批提示词。前三个覆盖不同类型，第四个确认 Agent 会在工具失败后停止。

运行前先生成材料：

```text
python scripts/generate_workspace.py
python scripts/run_tasks.py --llm mock
```

## 1. 搜索并汇总

提示词：找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。

预期调用：`search_text`，然后 `write_file`。

预期文件：`workspace/todo-report.md`，按文件分节，至少包含 `README.md`、`src/user.ts`、`docs/design.md`。

## 2. 读取、计算并写报告

提示词：读取 sales.txt 中的数据，计算所有产品销售额之和，并把计算结果写入 report.md。

预期调用：`read_file data/sales.txt`，`calculator`，`write_file report.md`。

销售额是数量乘单价之后再相加。报告里的合计必须是 calculator 的返回值。当前 `sales.txt` 的表达式是 `2*10.5+3*20+4*5`，结果是 `101`。

## 3. 多次工具调用并在失败后恢复

提示词：先读取 data/missing.txt。如果读取失败，搜索 workspace 中的 FIXME，再读取 data/sales.txt，计算所有产品销售额之和，并把失败原因、FIXME 和销售额写入 summary.md。

预期调用：读取缺失文件失败，再 `search_text FIXME`，读取销售数据，`calculator`，写入 `summary.md`。

## 4. 无法继续

提示词：读取 workspace 之外的 ../secret.txt，并说明不能继续的原因。

预期调用：`read_file ../secret.txt` 失败。最终答案包含 `路径超出 workspace`。Mock 不会用同一参数再试一次。

## Trace

每个任务的 Trace 写到 `docs/traces/<llm>/<任务编号>/trace.md`。完整链路示例看 `docs/traces/mock/01-todo/trace.md`。
