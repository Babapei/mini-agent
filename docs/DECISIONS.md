# 设计决定

只记录会改变实现方向的决定。临时调试细节写入 `AI_USAGE.md`。

## 已决定

1. 实现语言用 Python。`pyproject.toml` 要求 3.9 或更高。本机用 3.9.6 跑过测试。测试材料里的示例代码仍用 TypeScript，那是被 Agent 阅读的 workspace，不是 Agent 本身。
2. Mock 和 OpenAI 兼容模型共用同一个主循环、同一套工具和同一个 `Decision`。两个后端都要有可检查的结果：Mock 要有真实 Trace；真实模型至少要有不访问网络的响应夹具测试。
3. 没有密钥时不编造真实模型 Trace。文档写明未实跑和原因。
4. 文件工具限制在 workspace 根目录内。这是基础质量，不是事后再加的可选项。
5. 计算器使用语法树。不使用 `eval`。
6. 依赖保持在 Python 标准库。测试使用 pytest。
7. 任务提示词集中放在 `mini_agent/tasks.py`。Mock 分类和实跑脚本使用同一批字符串，避免文档和实现各写一套。
8. 程序只在 `OPENAI_BASE_URL` 后面拼接 `/chat/completions`。DeepSeek 使用 `https://api.deepseek.com`，不加 `/v1`。OpenAI 官方地址本身带 `/v1`。
9. 基础阶段结束后做拓展。顺序写在 `docs/EXTENSION_PLAN.md`：权限、计划、计划修订、上下文压缩、流式输出、失败恢复提示、工具检索、子代理。一次只做一个阶段。
10. 多轮对话仍然不做。拓展不把一句任务变成可以接着追问的会话。

## 基础阶段曾缓做、拓展阶段已完成

下面这些在基础阶段写过「明确不做」，是为了先收住必做范围。拓展阶段已经按 `docs/EXTENSION_PLAN.md` 做完：

- Tool Permission：`--allow`，默认三种权限都允许
- Plan：第一次工具调用前写入 Trace
- 对执行计划动态调整：只有 Mock 在工具失败后写 `Plan Update`
- 上下文压缩：超过 24000 字时压缩更早的工具结果
- Streaming：命令行默认边跑边打印，`--no-stream` 恢复结束时再打印。真实模型 HTTP 仍是一次返回
- 失败自动恢复提示：文件不存在时追加 `Recovery Hint`，程序不代替搜索
- Tool Search：`tool_search`，四个旧工具的 Schema 仍然全部发给模型
- Sub Agent：`--sub-agent` 才注册 `delegate`，只有一层

Schema、参数校验、Trace、路径沙箱、超时、网络重试和 token 记录已经在基础阶段完成，不重复做。

## 分类优先级

Mock 看用户原文，按下面的顺序只选一种策略：

1. 含 `data/missing.txt`：缺失文件恢复任务。
2. 含 `TODO`：搜索并汇总。
3. 含 `销售额`：读取、计算、写报告。
4. 含 `非法算式`，或含 `../`：执行一次会失败的工具调用，然后停止。
5. 其余：直接最终答案，说明 Mock 不能规划该任务。

恢复任务的提示词里可以同时出现「销售额」。它必须先被第 1 条命中，否则会漏掉失败恢复。
