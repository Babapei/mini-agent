# Mini Agent

一个用 Python 实现的命令行 Agent。它接收自然语言任务，自己决定调用 `read_file`、`write_file`、`search_text` 和 `calculator`，再根据工具结果决定下一步。Mock 和 OpenAI 兼容接口共用同一个主循环。

设计、阶段记录和门禁分别在 [docs/DESIGN.md](docs/DESIGN.md)、[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 和 [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)。

## 项目结构

先分清三件事：`mini_agent/` 是程序，`workspace/` 是模拟用户文件夹，`docs/traces/` 是跑完以后留下的逐步过程。根目录的 `docs/` 和 `workspace/docs/` 不是同一个目录。

带 `__init__.py` 的目录只是为了让 Python 能把它当作包来导入，里面没有业务逻辑。每次 Trace 目录里都有两份相同内容的记录：`trace.md` 给人读，`trace.jsonl` 一行一个事件给程序读。

```text
ths-written-test/
├── mini_agent/                         # Agent 程序本身
│   ├── __init__.py                     # 标记这是一个 Python 包
│   ├── __main__.py                     # 让 python -m mini_agent 能启动
│   ├── cli.py                          # 解析命令行参数，调用主循环，打印最终答案
│   ├── tasks.py                        # 四个固定任务的原文。Mock 和实跑脚本共用
│   ├── agent/
│   │   ├── __init__.py
│   │   └── loop.py                     # 主循环：问模型、执行工具、把结果塞回去、决定何时停止
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                     # 消息和决策的数据结构。Mock 与真实模型都用这一套
│   │   ├── mock.py                     # 假模型。只认识四句固定任务，按工具结果选择下一步
│   │   └── openai_compatible.py        # 真实模型适配器。调用 OpenAI 兼容接口
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                     # 工具的规格、参数校验、成功或失败结果
│   │   ├── registry.py                 # 按名字找到工具并调用。参数不合法时返回失败，不让程序崩溃
│   │   ├── read_file.py                # 读取 workspace 里的文本文件
│   │   ├── write_file.py               # 把文本写入 workspace
│   │   ├── search_text.py              # 在 workspace 里搜索一段文字，返回「文件:行号:内容」
│   │   ├── calculator.py               # 只做加减乘除。不使用 eval
│   │   └── sandbox.py                  # 禁止读到 workspace 外面，挡住 ../ 和越界符号链接
│   └── trace/
│       ├── __init__.py
│       └── recorder.py                 # 把每一步写成 trace.md 和 trace.jsonl
├── scripts/
│   ├── __init__.py                     # 让测试可以导入这两个脚本
│   ├── generate_workspace.py           # 生成或重置下面的测试材料 workspace/
│   └── run_tasks.py                    # 连续跑四个任务，检查报告和 Trace，并写 docs/results/mock.md
├── tests/                              # 自动测试。不产生给用户看的报告
│   ├── test_workspace.py               # 检查测试材料是否包含 TODO、FIXME、销售数据和失败输入
│   ├── test_tools.py                   # 检查四个工具、越界路径和非法算式
│   ├── test_mock.py                    # 检查假模型的下一步是哪个工具
│   ├── test_loop.py                    # 检查主循环的多轮调用、轮数上限和连续失败停止
│   ├── test_openai_adapter.py          # 用录好的响应检查真实模型适配器，不访问网络
│   └── test_run_tasks.py               # 检查缺少密钥时不会清掉 workspace 里已有的报告
├── workspace/                          # 模拟用户自己的文件夹。Agent 只能操作这里
│   ├── README.md                       # 用户文件夹里的说明，含一条 TODO
│   ├── src/user.ts                     # 普通代码，含 TODO
│   ├── src/order.ts                    # 普通代码，含 FIXME
│   ├── docs/design.md                  # 用户文件夹里的说明，含 TODO 和 FIXME。不是项目文档
│   ├── data/sales.txt                  # 产品、数量、单价。销售额任务读这个文件
│   ├── data/bad_expr.txt               # 内容是非法算式 2+，用来触发计算器失败
│   ├── data/missing.txt                # 故意不存在。恢复任务会先读它然后失败
│   ├── todo-report.md                  # 任务 1 跑完后写出的 TODO 汇总
│   ├── report.md                       # 任务 2 跑完后写出的销售额报告
│   └── summary.md                      # 任务 3 跑完后写出的失败恢复汇总
├── docs/                               # 项目文档和运行记录。Agent 不会把这里当作用户文件
│   ├── DESIGN.md                       # 设计说明：循环、工具、何时结束、失败怎么办
│   ├── PROJECT_PLAN.md                 # 分阶段计划，以及每一阶段做到了哪里
│   ├── DECISIONS.md                    # 已经定下的选择，以及明确不做的功能
│   ├── QUALITY_GATES.md                # 进入下一阶段前要满足的检查
│   ├── TASKS.md                        # 四个任务的提示词和预期结果
│   ├── AI_DIALOGUE.md                  # 和 AI 编程工具的主要对话过程
│   ├── prompts/system.md               # 交给真实模型的系统提示。Mock 不靠它做决定
│   ├── results/mock.md                 # 脚本四个任务的摘要：是否通过、轮数、最终答案。没有逐步过程
│   └── traces/                         # 每次运行的逐步过程
│       ├── mock/01-todo/               # 脚本任务 1：搜索 TODO 并写报告
│       ├── mock/02-sales/              # 脚本任务 2：读取销售数据、计算、写报告
│       ├── mock/03-recovery/           # 脚本任务 3：缺失文件失败后继续搜索和计算
│       ├── mock/04-blocked/            # 脚本任务 4：试图读取 workspace 之外的文件后停止
│       └── manual/                     # 手动执行 python -m mini_agent run 时留下的过程
├── exam_questions/                     # 笔试原题，本仓库只实现了第四题
│   ├── q1.md                           # 原题：日志分析。未实现
│   ├── q2.md                           # 原题：股票行情看板。未实现
│   ├── q3.md                           # 原题：训练 Sandbox 调度。未实现
│   ├── q4.md                           # 原题：Mini Agent。本项目实现的就是这一题
│   └── q5.md                           # 原题：Kubernetes 故障诊断。未实现
├── AI_USAGE.md                         # AI 参与了哪些环节、哪些决定是人做的、出过什么错
├── pyproject.toml                      # 项目名称、Python 版本、打包范围和 pytest 配置
├── README.md                           # 本说明
├── .gitignore                          # 告诉 Git 不要提交虚拟环境、缓存和打包产物
├── env/                                # 本地虚拟环境。已忽略，不提交
└── mini_agent.egg-info/                # pip 安装时生成的包装信息。已忽略，不提交
```

## 环境

本机用 Python 3.9.6 跑通过测试。声明的要求是 Python 3.9 或更高版本。

```text
python3 -m pip install pytest
```

运行本身只使用标准库。pytest 只用于测试。

## 生成测试材料

每次重新测试前先运行一次，清掉上一次写出的报告。否则真实模型会在 `workspace/` 里看到旧的 `report.md` 和 `summary.md`，等于提前看见答案。

```text
python3 scripts/generate_workspace.py
```

这会覆盖 `workspace/` 里的源文件，并删除 `todo-report.md`、`report.md` 和 `summary.md`。`data/missing.txt` 故意不存在。

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
