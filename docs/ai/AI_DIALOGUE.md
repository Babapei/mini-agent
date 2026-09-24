# AI 协作对话记录

这里记录开发 Mini Agent 时和 AI 编程工具的主要技术对话。候选人负责定范围、定设计和验收；AI 负责按这些决定实现、写测试和改文档。下面按主题整理核心来回，不是聊天工具的原始导出。技术结论以仓库里的代码为准。

## 读题，先定不做哪些

候选人：先读 `exam_questions/q4.md`，先不要写代码。我要确认你理解的是一个会自己调用工具的 Agent，不是一段直接写出 TODO 报告和销售额的脚本。你先列出基础要求、工具、测试材料和交付物。

AI：基础要求是十条：主循环、工具定义和注册、参数解析、工具调用、工具结果回到 Agent、根据结果决定下一步、一次任务里连续多次调用、最终答案、轮数上限、失败处理。工具至少有 `read_file`、`write_file`、`search_text`、`calculator`。workspace 要自己建，至少三种任务。交付物里有源代码、README、使用说明、测试材料、执行结果、完整 Trace、AI 对话、`AI_USAGE.md` 和设计说明。可选项包括 Schema、参数校验、权限、失败恢复、重试、超时、Trace、token、压缩、计划、子代理、流式输出、路径沙箱、工具查找、计划修订。

候选人：基础十条先做完，可选项先不进循环。多轮对话明确不做：一句任务结束，进程退出，没有「继续上一句」。语言用 Python，运行只依赖标准库，测试用 pytest。本机是 Python 3.9.6。Mock 和以后的真实模型必须是同一个 `run_agent`，不能写两套循环。计算器不许 `eval`。文件工具从第一天就限制在 workspace 里，这不是后面的可选项。没有密钥就不要编造 `docs/traces/openai/`。你把这些写成计划、设计、决定和每阶段门禁。阶段 0 只写文档。

AI：阶段 0 只改文档。后面每个阶段写明允许改的目录和验收命令，通过后再记完成。Mock 可以按任务原文选第一步，但文件内容、搜索命中和合计必须来自工具返回，不能在决定里写死 `101`。

候选人：执行方式再确认一次。我说分阶段，是做完一个我就看结果，不是你自己一口气做到最后。

AI：之前把「分阶段」理解成可以在同一次实现里连续写完。按你的要求改：阶段 0 结束就停；之后每次只做当前阶段，验收命令通过、完成记录写上，再进入下一阶段。

## 四层和一次决定

候选人：设计按职责切开。循环不读 CSV，也不汇总 TODO。模型只产出决定，不碰磁盘。工具做一件事，不选下一个工具。记录只把已经发生的事落成 `trace.md` 和 `trace.jsonl`。你按这四层写，不要写成四个任务的流程图。

AI：循环在 `mini_agent/agent/loop.py`，每轮调用 `decide(messages, tools)`。有 `tool_calls` 就按顺序执行，把 `ok` 和文本追加回消息。只有 `final_answer` 且该轮没有工具时结束。默认最多 12 轮。同一工具名加同一组参数连续失败 2 次就停。工具里的预期错误和未捕获异常都变成 `ok=false`，不抛出循环。

候选人：有一个顺序你必须写死。同一轮如果既有工具调用又有最终答案，只执行工具。结束必须是后面单独的一轮。否则模型还没看见工具结果就可以宣称写完了。

AI：`Decision` 里两类行动按这个优先级处理。`plan` 和后来的 `plan_update` 只是附在决定上的文字，不能代替工具，也不能让循环停止。

候选人：路径越界和以后的权限拒绝不要用同一句错误。越界是「路径超出 workspace」。权限是另一次检查，发生在调用处理函数之前。现在先做沙箱。`../`、绝对路径、指向外部的符号链接都要拒绝。计算器用语法树，只留数字、括号和 `+ - * / // % **`，指数绝对值大于 20 就拒绝。

AI：沙箱放在 `resolve_inside`。先相对 workspace 解析，再看真实路径是否仍在根目录内。计算器不调用 `eval` 或 `exec`。

## 材料和四句任务

候选人：workspace 里要有 TODO、FIXME、普通代码、销售数字、故意不存在的 `data/missing.txt`，以及会失败的路径和算式。任务至少三句，我定成四句，原文只写在 `mini_agent/tasks.py`，Mock 和 `scripts/run_tasks.py` 引用同一批字符串。不要文档里一套、代码里一套。

AI：四句是：搜索 TODO 并写 `todo-report.md`；读 `data/sales.txt`，用数量乘单价交给计算器，写 `report.md`；先读 `data/missing.txt`，失败后再搜 FIXME、读销售数据、计算、写 `summary.md`；读 `../secret.txt` 并说明不能继续。当前销售行是 Pen 2×10.5、Notebook 3×20、Paper 4×5，表达式是 `2*10.5+3*20+4*5`。合计只抄计算器返回的 `101`，不写进计划。

候选人：Mock 分类顺序写清楚，避免一句里同时像两个任务。`data/missing.txt` 优先于 TODO，否则恢复那句会因为别的词被分错。认不出的句子不要假装调用工具。

AI：分类顺序是：原文含 `data/missing.txt`，否则含 `TODO`，否则含「销售额」，否则含「非法算式」或 `../`，否则结束。最后一种的最终答案是「Mock 不能规划该任务。它只处理汇总 TODO、计算销售额、缺失文件恢复，以及越界或非法算式。」没有工具调用。

候选人：`search_text` 搜的是文件内容，不是文件名。这个写进工具说明。查 `sales` 不一定命中 `data/sales.txt`，因为文件名不参与匹配。

## 基础实现里的三处错误

候选人：阶段开始做。工具、Mock、循环、命令行按门禁来。pytest 收集失败你先看，不要改业务逻辑来绕。

AI：`tests/test_openai_adapter.py` 的响应类在注解里引用了自身，文件没有 `from __future__ import annotations`。Python 3.9 在收集测试时就 `NameError`，四个阶段的测试都没跑到断言。补上这行 import 后再执行 `python3 -m pytest`。

候选人：越界任务的 Trace 我看了，它就是读一次 `../secret.txt`，失败后停止，最终答案里有「路径超出 workspace」。你的脚本要求每条 Trace 都出现两段工具调用，所以把这个正确结果判失败了。检查按任务种类拆开。

AI：越界只断言一次 `read_file` 和那句路径错误。汇总、销售、恢复仍检查多步工具，以及报告是否来自工具结果。

候选人：我没配密钥，跑 `--llm openai` 之后 workspace 里的 `todo-report.md`、`report.md`、`summary.md` 没了，`docs/results/mock.md` 还写着通过。你先查脚本顺序，不要先猜是生成器把源文件覆盖坏了。

AI：`generate` 写在读取环境变量之前。缺 `OPENAI_API_KEY` 时函数已经把三份报告删掉，然后才返回退出码 2。把生成挪到凭证检查成功之后。补 `tests/test_run_tasks.py`：缺少密钥时不创建 Trace 目录，也不改已有报告。

## 接 DeepSeek

候选人：真实模型用我自己的密钥，不要写进仓库。`OPENAI_BASE_URL` 设为 `https://api.deepseek.com`，不要加 `/v1`。`OPENAI_MODEL` 用 `deepseek-flash`。程序只拼接 `/chat/completions`。官方 OpenAI 的地址本身有 `/v1`，你不要再帮它加或删。真实模型只记录，别用 Mock 那几句固定答案判通过或失败。

AI：请求体是 `model`、`temperature: 0`、消息和工具。工具规格转成 `type: function`，权限留在进程内，不放进 HTTP 的 function 对象。超时 30 秒。5xx、连接失败和超时最多再试 2 次，一共最多 3 次请求。状态码小于 500 立即失败。助手消息的 `content` 去掉空白后若非空，记为这一轮的 `plan`。适配器不设置 `plan_update`。响应不是 JSON、缺少 `choices`、工具参数不是对象，或没有工具调用却没有正文，都变成 `LLMError`，循环以「模型响应不可用」结束。

候选人：线上不要做成流式 HTTP。终端可以边跑边打印，那是本地回调。你若要测分片，只用录好的响应，参数 JSON 没收齐就不产生工具调用。

AI：`decide` 仍是一次 `urlopen` 读完整响应。`StreamAssembler` 只在夹具测试里拼分片。

候选人：四次我都看过 Trace。销售和恢复的 101 来自 `calculator`。越界那次没有读取 workspace 外面的文件。过程在 `docs/traces/openai/`。

## 拓展：每一项先定行为再写

候选人：基础阶段的「先不做」现在按 `docs/process/EXTENSION_PLAN.md` 做。顺序是权限、计划、计划修订、压缩、打印、恢复提示、工具查找、子代理。一次只做一项，测试通过再提交。四个旧任务在默认开关下必须还能过。

候选人：权限先做。`read`、`write`、`compute` 默认都允许。`--allow read` 时 `write_file` 和 `calculator` 在处理函数之前失败，文本是 `权限不足：<名称> 需要 <权限>`。不要写成「路径超出」。只读跑第 1 句时，搜索和读取可以成功，`todo-report.md` 不能被创建。

AI：检查放在 `ToolRegistry.execute` 里，位于 Schema 校验和 `handler` 之前。拒绝时返回失败结果，不抛出循环。

候选人：计划是决定上的 `plan`。只在这次运行的第一次工具调用之前写入 Trace 的 `Plan`。计划里不许出现合计 `101`。没有 `plan` 就不写这一节。真实模型若第一轮助手正文是空的，Trace 里就没有计划，这是允许的。

AI：循环用 `planned` 记住已经写过。OpenAI 适配器把非空 `content` 填进 `plan`。Mock 只在每类任务的第一次工具调用上带计划。

候选人：计划修订只在上一轮工具失败之后写。销售额第一次读取就成功时，Trace 里不能有 `Plan Update`。真实适配器不要去猜模型哪句话是修订，所以 DeepSeek 的 Trace 没有这一节。Mock 在恢复任务读缺失文件失败后要带上修订；越界任务在失败后的最终答案上带修订，说明不再用同一路径重试。

AI：`last_tool_failed` 只看上一轮最后一个工具。本轮 `plan_update` 非空且这个标志为真才写 `Plan Update`。

候选人：压缩不要加命令行开关去把 24000 改小。单条工具输出仍先截到 8000 字，末尾加「已截断」。全部消息超过 24000 字，且至少有两条工具消息时，除最后一条外收成 `已压缩：工具名 成功|失败：首行`，首行最多 80 字。已经是这前缀的不要再压一次。压缩不许再调用模型。四句短任务的 Trace 里不应出现 `Context Compression`。这条用测试把门槛降到 200 字来证明，测试目录用 pytest 的临时目录，不要写进 `docs/traces/`。

AI：`compress_context` 在每轮 `decide` 之前运行。只有返回的条数大于 0 才写 Trace。

候选人：打印是终端，不是 Trace，也不是流式 HTTP。默认先打 `tool: 工具名`，最终答案产生时再打答案。`--no-stream` 不注册回调，答案等 `run_agent` 返回后打一次。`tool_result` 事件不必打到终端，正文在 Trace 里。

AI：回调种类是 `tool_call`、`tool_result`、`final`。命令行只打印前一种和最后一种。

候选人：恢复提示的原文固定。`read_file` 的结果里有「文件不存在」、没有「路径超出」、并且是这个签名第一次失败，才追加：「恢复提示：文件不存在。可以用 search_text 按文件名查找，不要用同一路径再读一次。」程序不准自己调用 `search_text`。同一路径第二次失败仍按连续失败 2 次停止。越界不加这句。

AI：提示先放进 `pending_hints`。当时的实现是在该次工具返回后立刻追加到消息里。

候选人：`tool_search` 是只读工具。空查询失败，原文是「查询不能为空」。查找不到时返回空文本，但 `ok` 仍是真。四个旧工具的 Schema 继续全部发给模型。查找范围不要做成「注册表里现在有什么就搜什么」。

AI：实现时查找表写成固定五项：`read_file`、`write_file`、`search_text`、`calculator`、`tool_search`。`delegate` 即使后来注册了，也不在这五项里。空查询在 `strip` 之后判断。

候选人：子代理默认没有。`--sub-agent` 才注册 `delegate`，权限是 `read`，参数只有 `task`。空任务失败，原文「子任务不能为空」。子循环用同一个 `run_agent`，最多 6 轮，这 6 轮不占父循环的 12 轮，并且 `enable_delegate` 为假。子 Trace 写到 `sub/`。子循环状态不是 `final` 时，父循环收到的是失败结果，正文以「子任务失败：」开头，后面有子答案和 `子循环轮数：N`。不要自动再委托。Mock 的四句不会走到 `delegate`。一层行为用假模型测试。真实模型我用另一句任务另跑。

AI：父 Trace 只记这一次 `delegate` 的调用和结果。子文件在 `trace_dir/sub/`。

## 恢复提示的位置

候选人：单独跑缺失文件时，Trace 里有 `Recovery Hint`，看起来是对的。四句任务用 DeepSeek 一起跑时，恢复那次停了。你打开 `docs/traces/openai/03-recovery/trace.md` 和接口返回，不要先改提示原文。

AI：这一轮模型的一条助手消息里同时有 `read_file`，路径 `data/missing.txt`，以及 `search_text`。当时的代码在 `read_file` 失败后马上把恢复提示当成用户消息插进去，第二个工具结果写在这条用户消息之后。下一次请求被拒绝，HTTP 400，意思是带 `tool_calls` 的助手消息后面必须先跟上每一个 `tool_call_id` 的工具消息。

候选人：为什么 Mock 和单独那次 DeepSeek 没发现？

AI：Mock 的每一步只有一个工具调用，提示自然排在那一条工具消息后面，接口接受。单独的恢复实跑若第一轮也只有一个 `read_file`，提示同样在唯一的工具结果之后。四句一起跑时，模型把读缺失文件和搜索放进了同一次回复，提示才插到两条工具结果中间。原来的测试没有构造「一次决定、两个工具」。

候选人：提示留下。位置改成这一轮的工具结果全部写完之后。用测试锁住：同一次决定里先读 `data/missing.txt` 再搜 FIXME，下一轮模型看见的角色是助手、工具、工具、然后才是那条用户提示。我再只重跑恢复这一句。

AI：`pending_hints` 在循环里暂存。该轮 `for` 结束，或因为连续失败 2 次提前返回之前，调用 `_append_recovery_hints`。测试断言 Trace 里两节 `Tool Result` 都在 `Recovery Hint` 之前。

候选人：重跑后的 Trace 是三个工具结果都在，恢复提示在后面，计算器返回 101，`summary.md` 写上了。状态是 `final`。这次记录可以留。

## 一次跑完

候选人：`scripts/run_tasks.py` 扩展时，不要把 E2、E6 再各跑一遍。它们和第 2 句、第 3 句是同一句提示词。你先说清会覆盖哪些目录。我已经有 `docs/traces/deepseek-e1/` 到 `deepseek-e8/`，以及一批 `docs/traces/openai/`。

AI：`--llm mock` 重写 `docs/traces/mock/`（四句任务和 `e1-readonly`）以及 `docs/results/mock.md`。压缩、打印、`tool_search` 的空查询、一层子代理由 pytest 在临时目录跑，摘要里写通过或失败，不在 `docs/traces/` 下建目录。`--llm openai` 才会重写 `docs/traces/openai/`，并额外记录 `e1-readonly`、`e7-tool-search`、`e8-sub-agent`。`deepseek-e*` 不在这些输出路径里。

候选人：Mock 能判定的都放进这一次。真实模型不写 `Plan Update`，这一项就看 Mock 的 `03-recovery`，不要在 openai 结果里判失败。

AI：openai 模式的计划修订记为不适用。计划和恢复提示记为已记录，让人打开四个任务的 Trace 看 `## Plan` 和 `## Recovery Hint`。

## 设计说明和这两份记录

候选人：设计说明是给别人看的，写这个 Agent 怎么设计。重点是循环、消息、每个工具的参数和失败文本、权限、沙箱、下一层、两个后端、失败后怎么停、Trace 每一节何时出现。固定任务可以在最后提一句，不能变成测试说明书。写短了不行。题目那七个问题不要当成全文的目录，单独放在最后，按实现回答。写的时候对着代码，不要凭记忆。

AI：按 `loop.py`、`registry.py`、`mock.py`、`openai_compatible.py` 和各工具重写。文末第 14 节回答七个问题。核对时 `tool_search` 曾写成「搜索当前注册表」。函数 `_catalog` 只返回五项，没有 `delegate`。Mock 认不出任务时的整句也补回了，不是简称「无法规划」。

候选人：对话记录和 `AI_USAGE.md` 重写。不要贴原始聊天。要能看出是我定设计、你落地，我审到问题再问你，你说明原因并改代码。内容写全，细节和代码一致。
