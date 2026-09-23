# Mini Agent

一个用 Python 实现的命令行 Agent。它接收自然语言任务，自己决定调用 `read_file`、`write_file`、`search_text` 和 `calculator`，再根据工具结果决定下一步。Mock 和 OpenAI 兼容接口共用同一个主循环。

设计、阶段记录和门禁分别在 [docs/DESIGN.md](docs/DESIGN.md)、[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 和 [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)。

## 环境

需要 Python 3.11 或更高版本。本仓库在 Python 3.12 下用下面的命令验证过。当前环境里的命令是 `python3`。

```text
python3 -m pip install pytest
```

运行本身只使用标准库。pytest 只用于测试。

## 生成测试材料

```text
python3 scripts/generate_workspace.py
```

这会覆盖 `workspace/` 里的源文件，并删掉上一次任务留下的 `todo-report.md`、`report.md` 和 `summary.md`。`data/missing.txt` 故意不存在。

## 运行固定任务

```text
python3 scripts/run_tasks.py --llm mock
```

脚本会重新生成 workspace，依次执行四个任务，并检查输出和 Trace。通过后写到 [docs/results/mock.md](docs/results/mock.md)。Trace 在 `docs/traces/mock/<任务编号>/`。完整链路看 [docs/traces/mock/01-todo/trace.md](docs/traces/mock/01-todo/trace.md)。

四个任务的提示词和预期写在 [docs/TASKS.md](docs/TASKS.md)：

1. 搜索 TODO，按文件写入 `workspace/todo-report.md`。
2. 读取 `data/sales.txt`，用计算器求和，写入 `workspace/report.md`。当前合计是 `101`。
3. 先读不存在的 `data/missing.txt`，失败后搜索 FIXME、计算销售额，写入 `workspace/summary.md`。
4. 读取 `../secret.txt`。最终答案说明路径超出 workspace。

测试：

```text
python3 -m pytest
```

最近一次结果是 26 个测试通过，Mock 任务脚本通过。

## 单独执行一条任务

```text
python3 -m mini_agent run "找出 workspace 目录中所有 TODO，按照文件进行分类并生成 todo-report.md。" --workspace workspace --llm mock --max-steps 12 --trace-dir docs/traces
```

参数：

- `task`：交给 Agent 的自然语言任务。
- `--workspace`：工具允许访问的根目录，默认 `workspace`。
- `--llm`：`mock` 或 `openai`，默认 `mock`。
- `--max-steps`：最大决策轮数，默认 12。
- `--trace-dir`：写入 `trace.md` 和 `trace.jsonl` 的目录。

标准输出是最终答案。标准错误打印 `status`、`steps` 和 Trace 目录。workspace 不存在，或真实模型缺少配置时，退出码是 2。

## 真实模型

适配器调用 `POST ${OPENAI_BASE_URL}/chat/completions`。`OPENAI_BASE_URL` 需要带版本前缀，例如 `https://api.openai.com/v1`。

```text
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="..."
python3 scripts/run_tasks.py --llm openai
```

系统提示在 [docs/prompts/system.md](docs/prompts/system.md)。网络错误和 HTTP 5xx 最多再试 2 次。工具返回的业务失败不会在 HTTP 层重试。

本次交付时环境里没有这三个变量，所以没有真实模型 Trace，也没有把 Mock 结果标成真实模型结果。适配器由 `tests/test_openai_adapter.py` 用响应夹具验证，测试不访问网络。
