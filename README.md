# Mini Agent

一个用 Python 实现的命令行 Agent。它接收自然语言任务，自己决定调用 `read_file`、`write_file`、`search_text` 和 `calculator`，再根据工具结果决定下一步。`tool_search` 可以查找这些工具的说明。`delegate` 默认关闭，加上 `--sub-agent` 才能把一句子任务交给下一层。Mock 和 OpenAI 兼容接口共用同一个主循环。

设计、阶段记录和门禁分别在 [docs/DESIGN.md](docs/DESIGN.md)、[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 和 [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)。

## 项目结构

先分清三件事：`mini_agent/` 是程序，`workspace/` 是模拟用户文件夹，`docs/traces/` 是跑完以后留下的逐步过程。根目录的 `docs/` 和 `workspace/docs/` 不是同一个目录。

带 `__init__.py` 的目录只是为了让 Python 能把它当作包来导入，里面没有业务逻辑。每次 Trace 目录里都有两份相同内容的记录：`trace.md` 给人读，`trace.jsonl` 一行一个事件给程序读。

```text
ths-written-test/
├── mini_agent/                         # Agent 程序本身
│   ├── __init__.py                     # 标记这是一个 Python 包
│   ├── __main__.py                     # 让 python -m mini_agent 能启动
│   ├── cli.py                          # 解析命令行参数。可开关：--allow、--no-stream、--sub-agent
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
│   │   ├── tool_search.py              # 按字面量查找已有工具的名称和说明
│   │   ├── delegate.py                 # 子任务工具。默认不注册，--sub-agent 才启用，且只有一层
│   │   └── sandbox.py                  # 禁止读到 workspace 外面，挡住 ../ 和越界符号链接
│   └── trace/
│       ├── __init__.py
│       └── recorder.py                 # 把每一步写成 trace.md 和 trace.jsonl
├── scripts/
│   ├── __init__.py                     # 让测试可以导入这两个脚本
│   ├── generate_workspace.py           # 生成或重置下面的测试材料 workspace/
│   └── run_tasks.py                    # 连续跑四个任务。固定句子检查只在 --llm mock 时启用
├── tests/                              # 自动测试。不产生给用户看的报告
│   ├── test_workspace.py               # 检查测试材料是否包含 TODO、FIXME、销售数据和失败输入
│   ├── test_tools.py                   # 检查工具、权限、越界路径、非法算式和 tool_search
│   ├── test_mock.py                    # 检查假模型的下一步是哪个工具
│   ├── test_loop.py                    # 检查多轮调用、计划、压缩、流式回调、恢复提示和子代理
│   ├── test_openai_adapter.py          # 用录好的响应检查适配器和流式分片，不访问网络
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
│   ├── summary.md                      # 任务 3 跑完后写出的失败恢复汇总
│   └── out.md                          # 子代理实跑写出的 1+1 结果。重置材料时不会删除
├── docs/                               # 项目文档和运行记录。Agent 不会把这里当作用户文件
│   ├── DESIGN.md                       # 设计说明：循环、工具、何时结束、失败怎么办
│   ├── PROJECT_PLAN.md                 # 基础阶段计划，以及每一阶段做到了哪里
│   ├── EXTENSION_PLAN.md               # 拓展阶段计划。E1 到 E8 已完成，完成记录写在每一节末尾
│   ├── DECISIONS.md                    # 已经定下的选择。多轮对话不做，拓展阶段 E1 到 E8 已完成
│   ├── QUALITY_GATES.md                # 进入下一阶段前要满足的检查
│   ├── TASKS.md                        # 四个任务的提示词和预期结果
│   ├── AI_DIALOGUE.md                  # 和 AI 编程工具的主要对话过程
│   ├── prompts/system.md               # 交给真实模型的系统提示。Mock 不靠它做决定
│   ├── results/mock.md                 # Mock 四个任务的摘要：是否通过、轮数、最终答案
│   ├── results/openai.md               # --llm openai 四个任务的摘要。只记录，不判对错
│   └── traces/                         # 每次运行的逐步过程
│       ├── mock/01-todo/               # 脚本任务 1：搜索 TODO 并写报告
│       ├── mock/02-sales/              # 脚本任务 2：读取销售数据、计算、写报告
│       ├── mock/03-recovery/           # 脚本任务 3：缺失文件失败后继续搜索和计算
│       ├── mock/04-blocked/            # 脚本任务 4：试图读取 workspace 之外的文件后停止
│       ├── openai/                     # --llm openai 四个固定任务的逐步过程
│       ├── manual/                     # 早期手动执行 python -m mini_agent run 的过程
│       ├── e1-readonly/                # Mock 只读运行，写入被拒绝
│       ├── e5.png                      # DeepSeek 运行时终端先打印 tool: 的截图
│       ├── deepseek-e1/                # DeepSeek：--allow read，write_file 被拒绝
│       ├── deepseek-e2/                # DeepSeek：销售额任务，Plan 在第一次工具调用前
│       ├── deepseek-e6/                # DeepSeek：缺失文件后出现 Recovery Hint
│       ├── deepseek-e7/                # DeepSeek：tool_search 找到 calculator 后计算 1+1
│       └── deepseek-e8/                # DeepSeek：--sub-agent。子过程在 sub/
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

这会覆盖 `workspace/` 里的源文件，并删除 `todo-report.md`、`report.md` 和 `summary.md`。`workspace/out.md` 不在删除名单里。`data/missing.txt` 故意不存在。

## 运行固定任务

```text
python3 scripts/run_tasks.py --llm mock
```

`--llm mock` 会重新生成 workspace，依次执行四个任务，并按 Mock 的固定写法检查报告和 Trace。通过后写到 [docs/results/mock.md](docs/results/mock.md)。逐步过程在 `docs/traces/mock/<任务编号>/`。完整链路看 [docs/traces/mock/01-todo/trace.md](docs/traces/mock/01-todo/trace.md)。

真实模型用下面这条。密钥和地址见后面的「真实模型」一节。它同样会先重置 workspace，再跑四个任务，但只发请求，不检查对错。终端里的「已通过」只表示四次请求都跑完。摘要在 `docs/results/openai.md`，逐步过程在 `docs/traces/openai/<任务编号>/trace.md`。

```text
python3 scripts/run_tasks.py --llm openai
```

四个任务的提示词和预期写在 [docs/TASKS.md](docs/TASKS.md)：

1. 搜索 TODO，按文件写入 `workspace/todo-report.md`。
2. 读取 `data/sales.txt`，用计算器求和，写入 `workspace/report.md`。当前合计是 `101`。
3. 先读不存在的 `data/missing.txt`，失败后搜索 FIXME、计算销售额，写入 `workspace/summary.md`。
4. 读取 `../secret.txt`。最终答案说明路径超出 workspace。

测试：

```text
python3 -m pytest
```

最近一次结果是 44 个测试通过，Mock 任务脚本通过。`tests/` 检查的是程序行为，不代替下面的真实模型实跑。

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
- `--allow`：允许的权限，逗号分隔，默认 `read,write,compute`。例如 `--allow read` 时写入会失败，并且不创建文件。
- `--no-stream`：等任务结束后再打印最终答案。默认会先打印 `tool: 工具名`，再打印最终答案。
- `--sub-agent`：允许 `delegate`。子循环默认最多 6 轮，不能再委托。默认关闭。

默认会在工具调用和最终答案产生时就打印。标准错误仍在结束时打印 `status`、`steps` 和 Trace 目录。workspace 不存在，或真实模型缺少配置时，退出码是 2。

## 真实模型

适配器调用 `POST {OPENAI_BASE_URL}/chat/completions`。DeepSeek 的地址不带 `/v1`。

```text
export OPENAI_API_KEY="你的 DeepSeek 密钥"
export OPENAI_BASE_URL="https://api.deepseek.com"
export OPENAI_MODEL="deepseek-flash"
python3 scripts/run_tasks.py --llm openai
```

`--llm openai` 只向模型发请求，跑完四个任务。它不检查报告措辞，也不判断对错。终端里看到「已通过」只表示四次请求都跑完了。结果要自己看：

- 最终答案摘要：`docs/results/openai.md`
- 逐步过程：`docs/traces/openai/<任务编号>/trace.md`
- 写出的文件：`workspace/todo-report.md`、`workspace/report.md`、`workspace/summary.md`

系统提示在 [docs/prompts/system.md](docs/prompts/system.md)。网络错误和 HTTP 5xx 最多再试 2 次。工具返回的业务失败不会在 HTTP 层重试。

四个固定任务跑完后，过程在 `docs/traces/openai/`，摘要在 `docs/results/openai.md`。摘要里的状态是「已记录」。拓展项的实跑在 `docs/traces/deepseek-e1/`、`deepseek-e2/`、`deepseek-e6/`、`deepseek-e7/`、`deepseek-e8/`。`docs/traces/e5.png` 是终端先打印 `tool:` 再打印答案的截图。适配器另有 `tests/test_openai_adapter.py`，用录好的响应检查请求格式和流式分片，不访问网络。
