# Mini Agent 项目计划书

本文件是第四题的执行主线。阶段状态以这里为准。

## 防走偏规则

- 范围是第四题的 10 项基础能力、4 个工具、至少 3 个任务、1 份完整 Trace 和设计说明。
- 答案不能绕过工具。Mock 可以按任务关键词选择下一步，但文件内容、搜索命中和求和结果必须来自工具返回值。
- 每个阶段先核对本文的步骤，再改代码。阶段结束先跑验收命令，通过后把结论写回本文。
- 只改该阶段允许的目录。发现上一阶段缺陷时，先记入遗留问题，修完并复验后再继续。
- `AI_USAGE.md` 按阶段追加。

## 明确不做

多轮对话不在范围内。一句任务结束，进程退出。

基础阶段先不做、现已列入拓展的有：Tool Permission、Plan、计划动态调整、上下文压缩、Streaming、失败自动恢复提示、Tool Search、Sub Agent。顺序和步骤见 [EXTENSION_PLAN.md](EXTENSION_PLAN.md)。路径沙箱、Schema 校验、Trace、轮数上限、失败重试上限、token 记录已经在阶段 2 到阶段 7 完成。

## 阶段 0：计划书与设计冻结

- 状态：已完成
- 目标：把范围、职责、结束条件和门禁写死。不写业务代码。
- 允许目录：`docs/`、`AI_USAGE.md`
- 禁止：创建 `mini_agent/`、`workspace/`、`tests/`

步骤：

1. 写成本计划书。
2. 写 `docs/DESIGN.md`，回答 Loop、Tool 定义、结束条件、防无限调用、失败处理、四层职责、最大限制。
3. 写 `docs/DECISIONS.md`。
4. 写 `docs/QUALITY_GATES.md`。
5. 写 `AI_USAGE.md` 和 `docs/AI_DIALOGUE.md`，记录已经发生的选择。

验收：设计说明覆盖 7 问；「明确不做」已写明。

完成记录：

- 验收方式：阅读上述文档，核对 7 问和「明确不做」。
- 结果：文档已覆盖。阶段 0 结束时没有 `mini_agent/`。
- 遗留问题：无。

## 阶段 1：测试 workspace

- 状态：已完成
- 目标：生成可重复的测试材料。
- 允许目录：`scripts/generate_workspace.py`、`workspace/`、`tests/test_workspace.py`、本文完成记录
- 禁止：实现 Tool 或 Agent。

步骤：

1. 编写生成脚本，重复运行结果稳定。
2. 生成 `README.md`、`src/user.ts`、`src/order.ts`、`docs/design.md`、`data/sales.txt`。
3. 材料同时包含 TODO、FIXME、普通代码、数量与单价、说明文字、被引用但不存在的 `data/missing.txt`、失败输入 `../secret.txt` 与非法算式 `2+`。
4. `sales.txt` 使用 CSV 表头 `product,quantity,price`。

验收命令：

```text
python3 scripts/generate_workspace.py
python3 scripts/generate_workspace.py
python3 -m pytest tests/test_workspace.py
```

完成记录：

- 结果：`tests/test_workspace.py` 通过。重复生成的快照一致。`data/missing.txt` 不存在。`data/bad_expr.txt` 的内容是 `2+`。
- 遗留问题：无。

## 阶段 2：Tool 层

- 状态：已完成
- 目标：四个工具可独立调用。此阶段没有 Agent 循环。
- 允许目录：`mini_agent/tools/`、`mini_agent/__init__.py`、`tests/test_tools.py`、`pyproject.toml`、本文完成记录
- 禁止：LLM、主循环、CLI。

步骤：

1. 定义 Tool Schema：名称、描述、JSON 参数、必填项。
2. 注册表按名称调用。未知工具返回失败结果。
3. 参数校验失败返回失败结果，不抛到调用方之外。
4. `read_file`、`write_file`、`search_text` 的路径解析后必须仍在 workspace 内。
5. `search_text` 返回 `文件:行号:内容`。
6. `calculator` 只接受数字和四则运算，不使用 `eval`。
7. 测试覆盖成功、文件不存在、越界路径、非法表达式、空搜索。

验收命令：

```text
python3 -m pytest tests/test_tools.py
```

完成记录：

- 结果：`tests/test_tools.py` 通过。覆盖读取成功、文件不存在、`../` 与绝对路径、指向外部的符号链接、空搜索、空查询、非法表达式、未知工具和参数错误。
- 遗留问题：无。

## 阶段 3：LLM 接口与 Mock

- 状态：已完成
- 目标：统一 `Decision`。Mock 根据已有工具结果决定下一步。
- 允许目录：`mini_agent/llm/`、`mini_agent/tasks.py`、`tests/test_mock.py`、本文完成记录
- 禁止：完整主循环、真实 HTTP 调用。

步骤：

1. 定义 `Message`、`ToolCall`、`Decision`。
2. Mock 按用户原文分类，优先级为：`data/missing.txt`、`TODO`、`销售额`、越界或非法算式、其余无法规划。
3. TODO 任务：`search_text`，再 `write_file` 写 `todo-report.md`，再最终答案。
4. 销售额任务：`read_file data/sales.txt`，再 `calculator`，再 `write_file` 写 `report.md`，再最终答案。
5. 恢复任务：先读 `data/missing.txt`，失败后搜索 FIXME、读取销售额、计算并写入 `summary.md`。
6. 无法映射的任务直接给出最终答案，不假装调用了工具。

验收命令：

```text
python3 -m pytest tests/test_mock.py
```

完成记录：

- 结果：`tests/test_mock.py` 通过。销售额报告写入的合计使用工具返回的原文 `TOTAL-40`，Mock 源码没有写死 `101`。
- 遗留问题：无。

## 阶段 4：Agent 主循环

- 状态：已完成
- 目标：多轮工具调用、轮数上限、失败停止和 Trace。
- 允许目录：`mini_agent/agent/`、`mini_agent/trace/`、`tests/test_loop.py`、本文完成记录
- 禁止：真实网络请求。

步骤：

1. 循环：组 Context，请求 LLM，记 Trace，执行工具或结束。
2. 工具结果追加回 Context。
3. 默认最多 12 轮，可配置。
4. 同一工具、同一参数连续失败达到 2 次，停止并说明卡在哪里。
5. 工具异常变成失败结果，不中断进程。
6. 结束只有三种：最终答案、轮数耗尽、判定无法继续。
7. Trace 同时写 JSONL 和 Markdown。顺序包含 User、Agent Decision、Tool Call、Tool Result、Final Answer。
8. 工具输出超过长度上限时截断并注明。

验收命令：

```text
python3 -m pytest tests/test_loop.py
```

完成记录：

- 结果：`tests/test_loop.py` 通过。包含搜索后写入、改写销售数据后合计变为 `10`、同一失败调用两次后停止、轮数耗尽、长输出截断。
- 遗留问题：无。

## 阶段 5：真实模型适配器

- 状态：已完成（适配器已测，实跑待密钥）
- 目标：OpenAI 兼容接口，并用响应夹具测试，不访问网络。
- 允许目录：`mini_agent/llm/openai_compatible.py`、`docs/prompts/system.md`、`tests/test_openai_adapter.py`、本文完成记录
- 禁止：把 Mock Trace 写成真实模型结果。

步骤：

1. `POST {OPENAI_BASE_URL}/chat/completions`，工具使用 JSON Schema。
2. 环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。`OPENAI_BASE_URL` 需包含版本前缀，例如 `https://api.openai.com/v1`。
3. 系统提示放在 `docs/prompts/system.md`。
4. HTTP 超时和有限次重试只针对网络错误和 5xx。工具业务失败不在 HTTP 层重试。
5. 有 usage 时写入 Decision，供 Trace 记录。
6. 夹具覆盖工具调用、最终答案、畸形响应。

验收命令：

```text
python3 -m pytest tests/test_openai_adapter.py
```

完成记录：

- 结果：`tests/test_openai_adapter.py` 通过，测试没有访问网络。畸形 JSON、空 choices、无法解析的工具参数都会变成 `LLMError`。
- 遗留问题：环境没有密钥，真实任务还没有跑。见阶段 7。

## 阶段 6：CLI 与任务实跑

- 状态：已完成
- 目标：命令行跑通 Mock 任务，并留下完整 Trace。
- 允许目录：`mini_agent/cli.py`、`mini_agent/__main__.py`、`scripts/run_tasks.py`、`docs/TASKS.md`、`docs/traces/`、本文完成记录
- 禁止：为了让任务变绿而改写工具返回值或硬编码销售额。

步骤：

1. 实现 `python3 -m mini_agent run`。
2. 在 `docs/TASKS.md` 固定 4 个任务。
3. `scripts/run_tasks.py` 依次运行 Mock 任务并检查输出。
4. 保存至少一份完整 Markdown Trace。

验收命令：

```text
python3 scripts/generate_workspace.py
python3 scripts/run_tasks.py --llm mock
```

完成记录：

- 结果：四个 Mock 任务通过。`report.md` 的合计是 `101`，表达式是 `2*10.5+3*20+4*5`。`summary.md` 含缺失文件错误、FIXME 搜索行和同一个合计。越界任务的最终答案是 `无法继续：路径超出 workspace：../secret.txt`。完整 Trace 在 `docs/traces/mock/01-todo/trace.md`。
- 遗留问题：无密钥时的实跑脚本曾经先清空 workspace。已移到凭证检查之后，并补了回归测试。

## 阶段 7：真实模型实跑与文档收口

- 状态：已完成
- 目标：有密钥则实跑；无密钥则明确记录未执行。收口 README 和 AI_USAGE。
- 允许目录：`README.md`、`AI_USAGE.md`、`docs/AI_DIALOGUE.md`、`docs/DESIGN.md`、`docs/traces/openai/`、本文
- 禁止：编造真实模型 Trace。

步骤：

1. 检查密钥。有密钥则用 `--llm openai` 重跑任务 1 到 3。
2. 无密钥则在 README 和本文写明未执行及原因。
3. 收口 README：启动、参数、workspace 生成、任务、Trace 位置。
4. 对照交付清单勾选。
5. 补全 AI_USAGE。

验收命令：

```text
python3 scripts/generate_workspace.py
python3 -m pytest
python3 scripts/run_tasks.py --llm mock
```

有密钥时追加：

```text
python3 scripts/run_tasks.py --llm openai
```

完成记录：

- 结果：Mock 四个任务通过。DeepSeek 用 `deepseek-flash` 跑完四个任务，Trace 在 `docs/traces/openai/`。真实模型只记录结果，不按 Mock 的固定句子判对错。前三个任务写出了报告，越界任务在不调用工具的情况下说明不能继续。
- 遗留问题：无。基础阶段到此结束。

## 拓展阶段

状态以 [EXTENSION_PLAN.md](EXTENSION_PLAN.md) 为准。基础阶段的防走偏规则继续有效。顺序是：

1. E1 Tool Permission
2. E2 Plan
3. E3 对执行计划动态调整
4. E4 Context Compression
5. E5 Streaming
6. E6 Tool 调用失败自动恢复
7. E7 Tool Search
8. E8 Sub Agent

当前全部为未开始。E3 依赖 E2，E6 依赖 E3，E8 依赖 E1 和 E2，并且默认关闭。

## 第四题交付清单

- [x] 完整源代码
- [x] README
- [x] Agent 启动和使用说明
- [x] 测试 workspace 或生成脚本
- [x] 至少 3 个不同测试任务及实际执行结果
- [x] 至少一份完整 Agent Trace
- [x] AI 工具对话过程
- [x] AI_USAGE.md
- [x] 设计说明中的 7 个问题

## 基础能力清单

- [x] Agent 主循环
- [x] Tool 定义和注册
- [x] Tool 参数解析
- [x] Tool 调用
- [x] Tool Result 返回 Agent
- [x] 根据 Tool Result 判断下一步
- [x] 一次任务中连续调用多个 Tool
- [x] 最终答案输出
- [x] 执行轮数控制
- [x] Tool 调用失败处理
