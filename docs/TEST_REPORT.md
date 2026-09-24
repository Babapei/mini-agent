# 测试报告

这份报告摘自已经落盘的 Trace 和摘要，方便先看结论。逐步过程仍以 Trace 为准，不另附终端截图。打印顺序的终端画面在 `docs/traces/e5.png`。

最近一次本地全量测试是 `python3 -m pytest`，45 项通过。Mock 一次跑完的检查结果在 `docs/results/mock.md`，均为通过。DeepSeek（`deepseek-flash`，基地址 `https://api.deepseek.com`）一次跑完的记录在 `docs/results/openai.md`，模型条目为「已记录」，不按 Mock 的固定句子打分。

基础四句任务的过程见后文两张表。拓展八项都已实现，并且都有测试结果。有的和某句任务是同一次运行，所以没有单独的目录，不是没有测。

## 拓展项

| 项 | 测到的行为 | Mock | DeepSeek |
| --- | --- | --- | --- |
| E1 权限 | 只允许读时，`write_file` 在执行前被拒绝，文件不创建；`search_text` 和 `read_file` 仍成功 | 通过。`docs/traces/mock/e1-readonly/trace.md` 有 `权限不足：write_file 需要 write` | `docs/traces/openai/e1-readonly/trace.md`：写两次、计算两次均权限不足。另有 `docs/traces/deepseek-e1/` |
| E2 计划 | 第一次工具调用前有 `## Plan`，计划正文不含合计 `101` | 通过。看 `docs/traces/mock/02-sales/trace.md` | `docs/traces/openai/` 下各次运行都有 `## Plan`。另有 `docs/traces/deepseek-e2/` |
| E3 计划修订 | 上一轮工具失败后才有 `## Plan Update`；成功路径没有 | 通过。`03-recovery` 有，`02-sales` 没有 | 真实模型的适配器不写这一节，所以 DeepSeek 的 Trace 里没有。以 Mock 的 `03-recovery` 为准 |
| E4 压缩 | 超过长度时，更早的工具结果收成一行，最近一条仍是全文。短任务不出现 `Context Compression` | 自动测试通过，记在 `docs/results/mock.md` 的 `e4-e5-e7-e8-local`。四句任务的 Trace 里没有压缩节，因为输出太短 | 同一次 openai 命令里的同一组自动测试通过。短任务同样没有压缩节 |
| E5 打印 | 默认先打印 `tool: 工具名`，再打印最终答案。`--no-stream` 只在结束时打印答案 | 自动测试通过，同上 `e4-e5-e7-e8-local`。终端画面：`docs/traces/e5.png` | 同上。这是本地打印时机，线上 HTTP 仍是一次返回 |
| E6 恢复提示 | 文件不存在后有 `## Recovery Hint`，且在该轮全部工具结果之后。路径越界没有这节。程序不代替调用 `search_text` | 通过。`03-recovery` 有，`04-blocked` 没有 | `02-sales` 和 `03-recovery` 都有。另有 `docs/traces/deepseek-e6/` |
| E7 工具查找 | `tool_search` 用「计算」找到 `calculator`，再算出 `2`。空查询失败。四个旧工具不用先搜索也能调用 | 空查询和命中由自动测试通过，同上 `e4-e5-e7-e8-local`。四句固定任务不调用 `tool_search` | `docs/traces/openai/e7-tool-search/trace.md`：查询「计算」得到 `calculator`，`1+1` 的工具结果是 `2`。另有 `docs/traces/deepseek-e7/` |
| E8 子代理 | 默认没有 `delegate`。打开后只委托一层，子循环里有 `calculator` 得到 `2`，不能再委托 | 四句任务的 Trace 里没有 `delegate`。一层委托和子任务失败由自动测试通过，同上 `e4-e5-e7-e8-local` | `docs/traces/openai/e8-sub-agent/trace.md` 一次 `delegate`，子过程在 `sub/trace.md`。`out.md` 含 `1 + 1 = 2`。另有 `docs/traces/deepseek-e8/` |

## Mock

命令：`python3 scripts/run_tasks.py --llm mock`。过程在 `docs/traces/mock/`。

| 项 | 状态 | 轮数 | 结果 | Trace |
| --- | --- | --- | --- | --- |
| 汇总 TODO | final | 3 | 搜索到 3 条 TODO，写入 `todo-report.md`。`README.md:5`、`docs/design.md:5`、`src/user.ts:4` | `01-todo/trace.md` |
| 销售额 | final | 4 | 计算器返回 `101`，写入 `report.md`。`## Plan` 在第一次工具调用前，计划不含 `101`，没有 `## Plan Update` | `02-sales/trace.md` |
| 缺失文件后恢复 | final | 6 | 读 `data/missing.txt` 失败后有 `## Recovery Hint` 和 `## Plan Update`，再搜索 FIXME、计算并写入 `summary.md` | `03-recovery/trace.md` |
| 越界 | final | 2 | 最终答案含 `路径超出 workspace：../secret.txt`。没有 `## Recovery Hint` | `04-blocked/trace.md` |
| 只读 | final | 3 | `权限不足：write_file 需要 write`，未创建 `todo-report.md` | `e1-readonly/trace.md` |

压缩、终端打印顺序、`tool_search` 空查询、一层子代理由同一次命令里的自动测试完成，摘要节 `e4-e5-e7-e8-local` 为通过。这些检查使用临时目录，不另写 Trace。

## DeepSeek 一次跑完

命令：`python3 scripts/run_tasks.py --llm openai`。过程在 `docs/traces/openai/`。四句任务和只读、工具查找、子代理都有 `## Plan`。真实模型不写 `## Plan Update`，该项看 Mock 的 `03-recovery`。

| 项 | 状态 | 轮数 | 从 Trace 看到的结果 |
| --- | --- | --- | --- |
| 汇总 TODO | final | 5 | `search_text` 命中上述 3 条 TODO，`calculator` 把条数加总为 3，当时写入了 `todo-report.md`。随后的只读运行会删掉这个文件且写不回去，写入过程仍在 `01-todo/trace.md` |
| 销售额 | final | 10 | 先读 `sales.txt` 失败，随后有 `## Recovery Hint`。找到 `data/sales.txt` 后，`calculator` 计算 `2*10.5+3*20+4*5`，返回 `101`，写入 `report.md` |
| 缺失文件后恢复 | final | 6 | `read_file data/missing.txt` 返回文件不存在，`## Recovery Hint` 在该轮工具结果之后。FIXME 命中 `docs/design.md:6` 和 `src/order.ts:4`。`calculator` 返回 `101`，写入 `summary.md` |
| 越界 | final | 3 | 只在 workspace 内 `search_text` 和读取 `README.md`，没有读取 `../secret.txt`，没有写入文件，也没有 `## Recovery Hint` |
| 只读 | final | 8 | `search_text` 与 `read_file` 得到 3 条 TODO。`calculator` 两次均为 `权限不足：calculator 需要 compute`。`write_file` 两次均为 `权限不足：write_file 需要 write` |
| 工具查找 | final | 3 | `tool_search` 查询「计算」得到 `calculator`，再计算 `1+1`，工具返回 `2`。Trace：`e7-tool-search/trace.md` |
| 子代理 | final | 3 | 父循环一次 `delegate`。子 Trace `e8-sub-agent/sub/trace.md` 中 `calculator` 得到 `2`，没有再出现 `delegate`。父循环把结果写入 `out.md`，其中有 `1 + 1 = 2` |

同一次命令末尾的本地自动测试同样通过，见摘要的 `e4-e5-e7-e8-local`。

## 更早单独留下的 DeepSeek 记录

这些目录是同一类行为的另一次运行，脚本不会覆盖它们。

| 目录 | 内容 |
| --- | --- |
| `docs/traces/deepseek-e1/` | `--allow read`，`write_file` 被拒绝 |
| `docs/traces/deepseek-e2/` | 销售额任务，有 `## Plan`；先读 `sales.txt` 失败后有 `## Recovery Hint` |
| `docs/traces/deepseek-e6/` | 缺失文件任务，有 `## Recovery Hint` |
| `docs/traces/deepseek-e7/` | `tool_search` 找到 `calculator` 后算出 `2` |
| `docs/traces/deepseek-e8/` | 一次 `delegate`，子过程在 `sub/`，`calculator` 得到 `2` |

`docs/traces/e5.png` 是终端先打印 `tool:` 再打印最终答案的画面。
