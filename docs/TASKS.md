# 测试任务

同一句提示词，`scripts/run_tasks.py` 只跑一次。E2、E3、E6 是在这次结果里看不同标记，不是另一项任务。Mock 的过程在 `docs/traces/mock/`，真实模型在 `docs/traces/openai/`。你以前单独跑的 DeepSeek 在 `docs/traces/deepseek-e*`，那是同一句换了保存目录。

| 条目 | 脚本再跑一次吗 | 实际是哪一次 | 打开哪里看 |
| --- | --- | --- | --- |
| 1 TODO | 跑 | 自己这一句 | `01-todo` |
| 2 销售额 | 跑 | 自己这一句 | `02-sales` |
| 3 缺失文件 | 跑 | 自己这一句 | `03-recovery` |
| 4 越界 | 跑 | 自己这一句 | `04-blocked` |
| E1 只读 | 再跑 | 第 1 句，只允许读 | `e1-readonly` |
| E2 计划 | 不另跑 | 第 2 句 | `02-sales` 里的 `## Plan` |
| E3 计划更新 | 不另跑 | 第 3 句，并对照第 2 句 | `03-recovery` 有 `## Plan Update`，`02-sales` 没有。真实模型不写这一节 |
| E4 压缩 | 不跑任务 | 本地自动测试 | 短任务的 Trace 里没有 `已压缩` |
| E5 打印 | 不另存 Trace | 本地自动测试看终端。文后的单条命令会再跑第 1 句 | 终端先出现 `tool:`，再出现答案 |
| E6 恢复提示 | 不另跑 | 第 3 句，并对照第 4 句 | `03-recovery` 有 `## Recovery Hint`，`04-blocked` 没有 |
| E7 查找工具 | Mock 不跑这句；`--llm openai` 再跑 | 另一句提示词 | `e7-tool-search`，或 `deepseek-e7` |
| E8 子代理 | Mock 不跑这句；`--llm openai` 再跑 | 另一句，并打开 delegate | `e8-sub-agent`，或 `deepseek-e8` |

先进入项目根目录，并启用本地虚拟环境：

```text
source env/bin/activate
```

下面的命令都在这个目录里执行。每次单独跑任务前先重置材料，避免模型读到上一次写出的报告：

```text
python3 scripts/generate_workspace.py
```

这会删掉 `workspace/todo-report.md`、`workspace/report.md`、`workspace/summary.md`。`workspace/out.md` 不会删。

Mock 按固定句子检查对错。真实模型只发请求、只记录，终端里的「已通过」只表示请求跑完。看 Trace 和写出的文件判断结果。DeepSeek 在自己的终端里设置，不要把密钥写进仓库：

```text
export OPENAI_API_KEY="你的 DeepSeek 密钥"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-flash"
```

## 一次跑完

下面这一条会按文首的表把能在本地确认的都跑完。Mock 跑四个基础任务和只读，并在这些 Trace 里检查计划、计划更新、恢复提示。压缩、打印顺序、工具查找、一层子代理用自动测试判定，写在摘要的 `e4-e5-e7-e8-local`。

```text
python3 scripts/run_tasks.py --llm mock
```

通过后摘要在 `docs/results/mock.md`。过程在 `docs/traces/mock/01-todo/` 到 `04-blocked/`，以及 `docs/traces/mock/e1-readonly/`。

真实模型同样跑四个基础任务，再额外记录只读、工具查找和子代理。计划和恢复提示看这四个任务的 Trace，不另跑。计划更新仍只看 Mock。压缩和打印顺序仍用本地自动测试。真实模型的条目不判对错。

```text
python3 scripts/run_tasks.py --llm openai
```

摘要在 `docs/results/openai.md`。过程在 `docs/traces/openai/`，其中多出来的目录是 `e1-readonly/`、`e7-tool-search/`、`e8-sub-agent/`。这条会覆盖该目录里已有的记录。

下面各节的单条命令是只看一项、或换一个目录再存一份时用的。和一次跑完是同一句的，脚本不会再跑第二遍。

全部自动测试比这一条更多，包含更早的工具和路径检查：

```text
python3 -m pytest
```

## 四个基础任务

提示词和 `mini_agent/tasks.py` 是同一批。一次跑完会跑这四句，Mock 记在 `docs/traces/mock/`，真实模型记在 `docs/traces/openai/`。下面每节的命令是单独再跑一句，并写到 `docs/traces/manual-*`。预期调用按 Mock 的固定路径来写。真实模型可能多走几步。

### 1. 搜索并汇总

提示词：找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。

预期：`search_text`，然后 `write_file`。`workspace/todo-report.md` 按文件分节，至少包含 `README.md`、`src/user.ts`、`docs/design.md`。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。" --workspace workspace --llm mock --trace-dir docs/traces/manual-todo
```

把 `--llm mock` 换成 `--llm openai` 即用 DeepSeek。已有记录：`docs/traces/mock/01-todo/trace.md`、`docs/traces/openai/01-todo/trace.md`。

### 2. 读取、计算并写报告

提示词：读取 sales.txt 中的数据，计算所有产品销售额之和，并把计算结果写入 report.md。

预期：`read_file data/sales.txt`，`calculator`，`write_file report.md`。合计必须来自计算器。当前数据是 `2*10.5+3*20+4*5`，结果是 `101`。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "读取 sales.txt 中的数据，计算所有产品销售额之和，并把计算结果写入 report.md。" --workspace workspace --llm mock --trace-dir docs/traces/manual-sales
```

真实模型常会先读 `sales.txt` 失败，再找到 `data/sales.txt`。已有记录：`docs/traces/mock/02-sales/trace.md`、`docs/traces/openai/02-sales/trace.md`。

### 3. 缺失文件后恢复

提示词：先读取 data/missing.txt。如果读取失败，搜索 workspace 中的 FIXME，再读取 data/sales.txt，计算所有产品销售额之和，并把失败原因、FIXME 和销售额写入 summary.md。

预期：读取缺失文件失败，再 `search_text FIXME`，读取销售数据，`calculator`，写入 `summary.md`。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "先读取 data/missing.txt。如果读取失败，搜索 workspace 中的 FIXME，再读取 data/sales.txt，计算所有产品销售额之和，并把失败原因、FIXME 和销售额写入 summary.md。" --workspace workspace --llm mock --trace-dir docs/traces/manual-recovery
```

已有记录：`docs/traces/mock/03-recovery/trace.md`、`docs/traces/openai/03-recovery/trace.md`。

### 4. 越界后停止

提示词：读取 workspace 之外的 ../secret.txt，并说明不能继续的原因。

Mock 会调用 `read_file ../secret.txt`，失败后停止。最终答案包含 `路径超出 workspace`。真实模型可以不调用工具，直接说明不能读取 workspace 之外的文件。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "读取 workspace 之外的 ../secret.txt，并说明不能继续的原因。" --workspace workspace --llm mock --trace-dir docs/traces/manual-blocked
```

已有记录：`docs/traces/mock/04-blocked/trace.md`、`docs/traces/openai/04-blocked/trace.md`。

## E1 工具权限

一次跑完会把第 1 句再跑一遍，并且只允许读。Mock 记在 `docs/traces/mock/e1-readonly/`，真实模型记在 `docs/traces/openai/e1-readonly/`。`write_file` 失败，并且不创建文件。`read_file` 和 `search_text` 仍然成功。默认不加 `--allow` 时，三种权限都允许，四个基础任务照常通过。

下面是单独再存一份：

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。" --workspace workspace --llm mock --allow read --trace-dir docs/traces/e1-readonly
```

看 Trace：应有 `权限不足：write_file 需要 write`。确认没有 `workspace/todo-report.md`。以前的 DeepSeek 记录在 `docs/traces/deepseek-e1/`。

## E2 调用前的计划

和第 2 个基础任务是同一句，脚本不另跑。一次跑完已经在 `02-sales` 里检查：第一次工具调用之前有 `## Plan`，计划里不写死合计 `101`。摘要见 `docs/results/mock.md` 的 `e2-plan`。

没有单独开关。打开 `docs/traces/mock/02-sales/trace.md`，`## Plan` 在第一次 `## Tool Call` 之前。真实模型看 `docs/traces/openai/02-sales/trace.md`。以前单独存的一份在 `docs/traces/deepseek-e2/trace.md`。若模型第一轮没有写文字，Trace 里就不会有 `Plan`。

## E3 失败后的计划修订

和第 3 个基础任务是同一次，脚本不另跑。一次跑完已经检查：`03-recovery` 有 `## Plan Update`，`02-sales` 没有。摘要见 `docs/results/mock.md` 的 `e3-plan-update`。没有命令行开关。这一节只有 Mock 在上一轮工具失败后才会写。真实模型的 Trace 里不会出现。

打开 `docs/traces/mock/03-recovery/trace.md`。缺失文件的 `Tool Result` 之后、搜索 FIXME 的 `Tool Call` 之前，有 `## Plan Update`。打开 `docs/traces/mock/02-sales/trace.md`，第一次读取成功，里面没有 `## Plan Update`。

## E4 上下文压缩

没有命令行开关，也不能把 24000 字的门槛调低。短任务里不应出现 `已压缩` 或 `Context Compression`。一次跑完已经包含下面两条自动测试，结果在摘要的 `e4-e5-e7-e8-local`。

自动测试把门槛临时降到 200 字，检查最近一条工具结果仍是全文，更早的一条被收成一行。只跑这两条时用：

```text
python3 -m pytest tests/test_loop.py::test_compression_keeps_the_latest_tool_result tests/test_loop.py::test_short_sales_task_is_not_compressed -q
```

两条都通过即可。销售额这条短任务的 Trace 里没有压缩标记。

## E5 边跑边打印

一次跑完不另存 Trace。打印顺序已经包含在摘要的 `e4-e5-e7-e8-local` 里：先有 `tool: 工具名`，再有最终答案。看的是终端，不是 Trace。下面两条命令是手动看终端时再跑第 1 句。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。" --workspace workspace --llm mock --trace-dir docs/traces/manual-stream
```

加上 `--no-stream` 后，工具名不再出现，最终答案等任务结束才打印：

```text
python3 -m mini_agent run "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。" --workspace workspace --llm mock --no-stream --trace-dir docs/traces/manual-nostream
```

终端截图在 `docs/traces/e5.png`。真实模型的 HTTP 仍是一次返回，这里只改变本地打印时机。

## E6 文件不存在时的恢复提示

和第 3 个基础任务是同一句，脚本不另跑。一次跑完已经检查：`03-recovery` 有 `## Recovery Hint`，`04-blocked` 没有。摘要见 `docs/results/mock.md` 的 `e6-recovery-hint`。`read_file` 报告文件不存在后，提示出现在这一轮全部工具结果之后，不插在同一次回复的结果中间。下一步搜索由模型自己决定，程序不代替调用 `search_text`。路径越界不会出现这句提示。

下面的单条命令是手动再存一份时用的。

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "先读取 data/missing.txt。如果读取失败，搜索 workspace 中的 FIXME，再读取 data/sales.txt，计算所有产品销售额之和，并把失败原因、FIXME 和销售额写入 summary.md。" --workspace workspace --llm mock --trace-dir docs/traces/manual-recovery
```

看 Trace 里的 `## Recovery Hint`。Mock 记录在 `docs/traces/mock/03-recovery/trace.md`。DeepSeek 记录在 `docs/traces/openai/03-recovery/trace.md` 和 `docs/traces/deepseek-e6/trace.md`。越界任务 `docs/traces/mock/04-blocked/trace.md` 里没有这一节。

## E7 查找工具

四个旧工具不用先搜索也能直接调用，所以上面四个基础任务不会用到 `tool_search`。Mock 不认识下面这句自由任务。一次跑完的 Mock 只跑自动测试，确认 `计算` 能找到 `calculator`、空查询会失败，结果在 `e4-e5-e7-e8-local`。`--llm openai` 会再跑这句，记在 `docs/traces/openai/e7-tool-search/`。

下面是以前单独存到 `deepseek-e7` 的命令。Trace 里应有 `tool_search`，返回里有 `calculator`，随后 `calculator` 的结果是 `2`。

```text
python3 -m mini_agent run "先用 tool_search 查找哪个工具负责计算，再用它计算 1+1，不要自己心算。" --workspace workspace --llm openai --trace-dir docs/traces/deepseek-e7
```

只跑自动测试时用：

```text
python3 -m pytest tests/test_tools.py::test_tool_search_finds_calculator_and_rejects_empty_query -q
```

## E8 子代理

默认没有 `delegate`。Mock 的四个基础任务不会委托，一次跑完的 `docs/traces/mock/` 里不应出现 `delegate`。Mock 不能规划下面这句自由任务。一层子循环、子任务失败后回到父循环，由自动测试里的假模型完成，结果在 `e4-e5-e7-e8-local`。`--llm openai` 会打开 delegate 再跑这句，记在 `docs/traces/openai/e8-sub-agent/`，子过程在同目录的 `sub/`。

下面是以前单独存到 `deepseek-e8` 的命令：

```text
python3 scripts/generate_workspace.py
python3 -m mini_agent run "使用 delegate，把「用 calculator 计算 1+1」交给下一层。拿到子任务答案后，写入 out.md。" --workspace workspace --llm openai --sub-agent --trace-dir docs/traces/deepseek-e8
```

父 Trace 里有一次 `delegate`。子过程在 `docs/traces/deepseek-e8/sub/trace.md`，里面有 `calculator` 得到 `2`，不能再出现 `delegate`。`workspace/out.md` 里有 `1 + 1 = 2`。

只跑自动测试时用：

```text
python3 -m pytest tests/test_loop.py::test_delegate_is_absent_for_the_default_todo_task tests/test_loop.py::test_delegate_runs_one_child_level tests/test_loop.py::test_failed_child_returns_to_parent_once -q
```
