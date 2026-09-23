# 拓展阶段计划

基础阶段（阶段 0 到阶段 7）已经完成。本文是后面可选项的执行顺序。一次只做一个阶段。该阶段的测试通过、完成记录写回本文之后，才开始下一阶段。

仍然不做多轮对话。一句任务结束，进程退出，不保留给下一句用户消息。

每一阶段都要守住这些规则：

- Mock 的四个任务继续按固定句子检查通过。
- 销售额、搜索命中、文件内容仍然来自工具返回，不写死在计划或摘要里。
- 默认行为与现在一致。新能力用开关打开，避免四个旧任务突然改道。
- 真实模型不自动判对错。行为有变化时，用夹具或假模型测循环；DeepSeek 只在该阶段需要看真实措辞时手动跑一句。
- 只改该阶段列出的文件。发现上一阶段的缺陷，先记进遗留，修完并复验再继续。

## 已有、不再单独立项

这些在题目里算可选项，基础阶段已经做了：

- Tool Schema、参数校验
- Agent Trace
- 禁止读取 workspace 之外的文件
- HTTP 超时，以及网络错误和 5xx 的有限次重试
- Trace 中的 token 用量
- 工具失败交回模型，同一调用连续失败 2 次停止

## E1：Tool Permission

- 状态：已完成
- 目标：每个工具声明自己是只读、可写还是计算。调用前按本次运行允许的权限拒绝，不执行工具。
- 允许目录：`mini_agent/tools/`、`mini_agent/cli.py`、`mini_agent/agent/loop.py`、`tests/test_tools.py`、`tests/test_loop.py`、本文

步骤：

1. 在工具规格上增加权限：`read_file` 和 `search_text` 为只读，`write_file` 为可写，`calculator` 为计算。
2. 运行参数默认三种都允许，与现在相同。
3. 增加 `--allow`，例如 `--allow read,compute`。未列入的权限直接返回失败结果，不写文件、不抛到循环外。
4. 失败文本写明工具名和被拒绝的权限。Trace 里看得到这次拒绝。
5. 路径沙箱保持原样。权限拒绝和路径越界是两道不同的失败。

验收：

- 只允许读取时，`write_file` 失败，目标文件不存在。
- 只允许读取时，`read_file` 和 `search_text` 仍成功。
- 默认权限下，`python3 scripts/run_tasks.py --llm mock` 仍然通过。
- `pytest` 通过。

完成记录：

- 结果：工具规格带 `permission`。`read_file`、`search_text` 为 `read`，`write_file` 为 `write`，`calculator` 为 `compute`。注册表在执行前检查本次允许的权限，拒绝时返回 `权限不足：<工具名> 需要 <权限>`，不调用处理函数。CLI 增加 `--allow`，默认 `read,write,compute`。只读测试确认 `write_file` 不创建文件，`read_file` 和 `search_text` 仍成功，拒绝文本进入 Trace。路径越界仍是原来的沙箱错误。`pytest` 30 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E2：Plan

- 状态：已完成
- 目标：动手调用工具之前，先有一份短计划，并写进 Trace。
- 允许目录：`mini_agent/llm/`、`mini_agent/agent/loop.py`、`mini_agent/trace/`、`docs/prompts/system.md`、`tests/test_mock.py`、`tests/test_loop.py`、本文

步骤：

1. 决策增加可选的 `plan` 字段。没有计划时不改变工具调用。
2. 主循环在第一次工具调用之前，若还没有计划，先记一节 `Plan`。
3. Mock 按四类任务各给出一段计划：搜索后按文件写报告、读取后计算再写报告、先读缺失文件再恢复、尝试越界读取后停止。计划不代替下一步工具调用。
4. 真实模型的系统提示要求第一轮先给出计划，再调用工具。计划文本不参与对错判断。
5. Trace 顺序变为：User、Plan、Agent Decision、Tool Call、Tool Result，最后是 Final Answer。已有测试若只要求原来的顺序作为子序列，保持能通过。

验收：

- Mock 的 TODO 任务 Trace 含有 `Plan`，且出现在第一次 `Tool Call` 之前。
- 计划里不出现写死的合计 `101`。
- `python3 scripts/run_tasks.py --llm mock` 通过。
- `pytest` 通过。

完成记录：

- 结果：`Decision` 增加可选 `plan`。Mock 四类任务只在第一次工具调用时带上计划，计划里没有写死合计。主循环在第一次工具调用前把计划写成 Trace 的 `Plan`。没有计划时工具调用不变。真实模型若在工具调用的消息里写了计划文本，同样记入 `Plan`；系统提示要求第一轮先写计划再调用工具。`pytest` 30 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E3：对执行计划动态调整

- 状态：已完成
- 目标：工具失败后留下一份计划修订，说明下一步为什么改道。
- 允许目录：`mini_agent/llm/mock.py`、`mini_agent/agent/loop.py`、`mini_agent/trace/`、`tests/test_mock.py`、`tests/test_loop.py`、本文
- 依赖：E2 已完成。

步骤：

1. Trace 增加 `Plan Update`。只有上一轮工具失败时才允许出现。
2. Mock 的恢复任务在 `data/missing.txt` 失败后，修订计划写明改去搜索 FIXME，再读销售数据并计算。
3. 成功路径不写修订。越界任务若第一次调用就失败，修订计划写明不再用同一路径重试。
4. 真实模型不强制句式。循环只在决策带了新计划时记录修订。
5. 修订计划不能直接调用工具。工具调用仍走原来的决策。

验收：

- 恢复任务的 Trace 在缺失文件失败之后、搜索 FIXME 之前，有 `Plan Update`。
- 销售额任务在第一次读取就成功时，没有 `Plan Update`。
- Mock 四个任务仍然通过。
- `pytest` 通过。

完成记录：

- 结果：决策增加 `plan_update`。只有上一轮工具失败时，主循环才把它写成 `Plan Update`，并且写在下一次工具调用之前。修订文本本身不调用工具。Mock 的恢复任务在缺失文件失败后写明改去搜索 FIXME；越界任务写明不再用同一路径重试。销售额成功路径没有 `Plan Update`。`pytest` 32 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E4：Context Compression

- 状态：已完成
- 目标：工具结果变长时，压缩更早的结果，保留最近一条全文。
- 允许目录：`mini_agent/agent/loop.py`、`tests/test_loop.py`、`docs/DESIGN.md`、本文

步骤：

1. 把组上下文从主循环里抽出来，单独函数负责截断和压缩。
2. 默认阈值沿用单条 8000 字截断。另加一个总长度阈值，测试里可以调低。
3. 超过总长度时，除最近一条工具结果外，更早的工具结果收成一行：工具名、成败、首行摘要。最近一条保持全文。
4. 压缩不调用模型，避免摘要再发明数字。
5. Trace 在发生压缩时写明压缩了几条。未超过阈值时，Trace 与现在一致。

验收：

- 用假模型和一长串工具结果，断言送给模型的最近一条是全文，更早的一条含有压缩标记。
- 销售额这条短任务的消息里没有压缩标记。
- Mock 四个任务通过。
- `pytest` 通过。

完成记录：

- 结果：上下文组装抽成 `compress_context`。单条仍按 8000 字截断。全部消息超过 24000 字时，最近一条工具结果保持全文，更早的收成 `已压缩：工具名 成败：首行`。压缩不调用模型。发生压缩时 Trace 写明条数，未超过阈值时 Trace 不增加这一节。`pytest` 34 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E5：Streaming

- 状态：已完成
- 目标：命令行在工具调用和最终答案产生时就打印，而不是等整句任务结束。
- 允许目录：`mini_agent/agent/loop.py`、`mini_agent/cli.py`、`mini_agent/llm/openai_compatible.py`、`tests/test_loop.py`、`tests/test_openai_adapter.py`、本文

步骤：

1. 主循环增加可选的事件回调：决策、工具结果、最终答案片段。不传回调时，行为与现在相同。
2. 命令行默认打开回调，每轮打印工具名和最终答案。`--no-stream` 恢复为只在结束时打印最终答案。
3. Mock 的最终答案按回调一次交出。不模拟网络分片。
4. 真实模型先保持非流式 HTTP。流式解析放在回调稳定之后，单独用录好的分片响应测试，不访问网络。
5. 工具参数未收齐时不执行工具。

验收：

- 假模型跑 TODO 任务，回调先收到搜索的工具调用，再收到最终答案。
- `--no-stream` 的测试不依赖打印顺序。
- Mock 四个任务通过。
- `pytest` 通过。

完成记录：

- 结果：主循环增加可选 `on_event`。不传回调时，结束方式和打印方式与原来相同。命令行默认打印 `tool: 工具名`，并在最终答案产生时打印；`--no-stream` 仍等任务结束后打印一次最终答案。Mock 的最终答案只通过回调交一次。真实模型的 HTTP 仍是非流式。`StreamAssembler` 用录好的分片测试，参数 JSON 未收齐时不产出工具调用。`pytest` 38 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：线上请求还没有改成流式 HTTP。分片解析只在测试里使用。

## E6：Tool 调用失败自动恢复

- 状态：已完成
- 目标：文件不存在时，给模型一条明确的恢复提示，由模型决定要不要搜索。程序不偷偷改调用下一个工具。
- 允许目录：`mini_agent/agent/loop.py`、`tests/test_loop.py`、本文
- 依赖：E3 已完成。若恢复提示和计划修订重复，只保留一处，并在完成记录里写明。

步骤：

1. `read_file` 返回「文件不存在」时，向上下文追加一条提示：可以用 `search_text` 按文件名查找，不要用同一路径再读一次。
2. 提示不是工具调用，Trace 里单独标成恢复提示。
3. 同一路径第二次仍然失败时，沿用连续失败 2 次就停止的规则。
4. 路径越界不追加「换路径再找」的提示。越界不是找错文件名。
5. 用假模型验证提示出现一次，且循环没有自行发出 `search_text`。

验收：

- 缺失文件后的下一次决策看得到恢复提示。
- 越界失败后的上下文里没有这条提示。
- Mock 四个任务通过。
- `pytest` 通过。

完成记录：

- 结果：`read_file` 返回「文件不存在」时，上下文追加一条用户消息，Trace 单独记为 `Recovery Hint`。提示建议用 `search_text` 按文件名找，并且不要用同一路径再读。程序没有代替模型发出搜索。同一路径第二次失败仍按连续失败 2 次停止。路径越界不追加这条提示。计划修订和恢复提示都保留：前者是模型的改道说明，后者是交给下一次决策看的提示。`pytest` 40 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E7：Tool Search

- 状态：已完成
- 目标：增加一个 `tool_search`，按字面量查找已有工具的名称和说明。
- 允许目录：`mini_agent/tools/`、`tests/test_tools.py`、`docs/prompts/system.md`、本文

步骤：

1. 新工具为只读。参数是 `query`。返回匹配到的工具名和一句话说明。
2. 四个旧工具的 Schema 继续全部发给模型。本阶段不隐藏工具，避免四个任务必须先搜索工具。
3. 权限沿用 E1。未做 E1 时，`tool_search` 按只读处理。
4. 系统提示说明：工具少的时候可以直接调用；不确定工具用途时再搜索。
5. 测试 `计算` 能找到 `calculator`，空查询失败，找不到时返回空结果而不是异常。

验收：

- `pytest tests/test_tools.py` 通过。
- Mock 四个任务不调用 `tool_search` 也仍然通过。
- `pytest` 通过。

完成记录：

- 结果：新增只读工具 `tool_search`，按字面量匹配工具名和说明。`计算` 能找到 `calculator`。空查询失败。找不到时返回空文本，不抛异常。四个旧工具的 Schema 仍然全部发给模型，Mock 四个任务不调用 `tool_search` 也通过。系统提示说明工具少时直接调用。`pytest` 41 项通过，`python3 scripts/run_tasks.py --llm mock` 通过。
- 遗留问题：无。

## E8：Sub Agent

- 状态：未开始
- 目标：主 Agent 可以把一句子任务交给同一个循环的下一层，并拿回子任务的最终答案。
- 允许目录：`mini_agent/tools/`、`mini_agent/agent/loop.py`、`mini_agent/cli.py`、`tests/test_loop.py`、本文
- 依赖：E1、E2 已完成。默认关闭。

步骤：

1. 增加可写权限之外的工具 `delegate`，参数只有子任务文本。默认不注册。`--sub-agent` 才注册。
2. 子循环使用同一个 workspace、同一套工具，但不能再注册 `delegate`。深度只有一层。
3. 子循环有自己的轮数上限，默认 6，计入调用方可见的返回文本，不单独吃掉父循环的全部 12 轮。
4. 子 Trace 写到本次 Trace 目录的 `sub/`。父 Trace 记录一次 `delegate` 调用和子任务的最终答案。
5. 用假模型测试：父任务委托「计算 1+1」，子循环调用计算器，父循环把子答案写入文件。Mock 的四个固定任务在默认关闭时不受影响。
6. 子循环失败时，父循环收到失败结果，可以停止或改计划。不得无限委托。

验收：

- 未加 `--sub-agent` 时，工具列表里没有 `delegate`，Mock 四个任务通过。
- 打开后，假模型的委托测试通过，且子循环里没有第二层 `delegate`。
- `pytest` 通过。

完成记录：

- 结果：
- 遗留问题：

## 做完之后

八个阶段都完成后，更新 `docs/DESIGN.md` 的「最大限制」，把已经落地的能力从限制里移出。README 的项目结构补上新工具和开关。真实模型仍由人看 Trace，不把 Mock 的固定句子套上去。
