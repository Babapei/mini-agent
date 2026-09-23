"""按固定任务句式决策，并把下一步建立在工具结果上。"""

from __future__ import annotations

from mini_agent.llm.base import Decision, Message, ToolCall

_UNKNOWN_ANSWER = (
    "Mock 不能规划该任务。它只处理汇总 TODO、计算销售额、缺失文件恢复，以及越界或非法算式。"
)


def classify(text: str) -> str:
    if "data/missing.txt" in text:
        return "recovery"
    if "TODO" in text:
        return "todo"
    if "销售额" in text:
        return "sales"
    if "非法算式" in text or "../" in text:
        return "blocked"
    return "unknown"


def sales_expression(csv_text: str) -> str:
    lines = [line.strip() for line in csv_text.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("销售数据为空")
    header = [part.strip() for part in lines[0].split(",")]
    if header != ["product", "quantity", "price"]:
        raise ValueError("销售数据表头无法识别")
    terms: list[str] = []
    for line in lines[1:]:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            raise ValueError("销售数据行列数不正确")
        _product, quantity, price = parts
        if not _is_number(quantity) or not _is_number(price):
            raise ValueError("销售数据不是数字")
        terms.append(f"{quantity}*{price}")
    return "+".join(terms)


def render_todo_report(search_output: str) -> str:
    groups: dict[str, list[tuple[str, str]]] = {}
    order: list[str] = []
    for raw in search_output.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"搜索结果无法解析：{line}")
        path, lineno, text = parts
        groups.setdefault(path, [])
        if path not in order:
            order.append(path)
        groups[path].append((lineno, text.strip()))
    lines = ["# TODO Report", ""]
    if not order:
        lines.append("没有找到 TODO。")
        return "\n".join(lines) + "\n"
    for path in order:
        lines.append(f"## {path}")
        lines.append("")
        for lineno, text in groups[path]:
            lines.append(f"- 第 {lineno} 行：{text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_sales_report(expression: str, total: str) -> str:
    return f"# Sales Report\n\n销售额合计：{total.strip()}\n\n表达式：{expression}\n"


def render_summary(missing_error: str, fixmes: str, expression: str, total: str) -> str:
    fixme_body = fixmes.strip() or "没有找到 FIXME。"
    return (
        "# Summary\n\n"
        "## 缺失文件\n\n"
        f"data/missing.txt 读取失败：{missing_error.strip()}\n\n"
        "## FIXME\n\n"
        f"{fixme_body}\n\n"
        "## 销售额\n\n"
        f"表达式：{expression}\n\n"
        f"合计：{total.strip()}\n"
    )


class MockLLM:
    def decide(self, messages: list[Message], tools: list[dict]) -> Decision:
        del tools
        user = _user_text(messages)
        done = [message for message in messages if message.role == "tool"]
        kind = classify(user)
        if kind == "todo":
            return _todo(done)
        if kind == "sales":
            return _sales(done)
        if kind == "recovery":
            return _recovery(done)
        if kind == "blocked":
            return _blocked(user, done)
        return _final(_UNKNOWN_ANSWER)


_PLANS = {
    "todo": "搜索 TODO，按文件归类后写入 todo-report.md。",
    "sales": "读取销售数据，把数量与单价交给计算器求和，再写入 report.md。",
    "recovery": "先读取 data/missing.txt。若失败，改为搜索 FIXME，再读取销售数据并计算，最后写入汇总。",
    "blocked": "按任务尝试一次读取或计算。若路径越界或算式非法，就停止，不再用同一调用重试。",
}


def _todo(done: list[Message]) -> Decision:
    if not done:
        return _call(
            "需要先搜索 workspace 中的 TODO",
            "search_text",
            {"query": "TODO"},
            plan=_PLANS["todo"],
        )
    if len(done) == 1:
        if not done[0].ok:
            return _final(f"无法继续：搜索失败：{done[0].content}")
        try:
            report = render_todo_report(done[0].content)
        except ValueError as exc:
            return _final(f"无法继续：{exc}")
        return _call(
            "按文件归类搜索结果并写入报告",
            "write_file",
            {"path": "todo-report.md", "content": report},
        )
    if len(done) == 2:
        if not done[1].ok:
            return _final(f"无法继续：写入失败：{done[1].content}")
        return _final("已根据搜索结果按文件汇总 TODO，并写入 todo-report.md。\n" + done[0].content)
    return _final("无法继续：TODO 任务的工具调用次数超出 Mock 计划。")


def _sales(done: list[Message]) -> Decision:
    if not done:
        return _call("先读取销售数据", "read_file", {"path": "data/sales.txt"}, plan=_PLANS["sales"])
    if len(done) == 1:
        if not done[0].ok:
            return _final(f"无法继续：读取销售数据失败：{done[0].content}")
        try:
            expression = sales_expression(done[0].content)
        except ValueError as exc:
            return _final(f"无法继续：{exc}")
        return _call("用计算器求销售额合计", "calculator", {"expression": expression})
    if len(done) == 2:
        if not done[1].ok:
            return _final(f"无法继续：计算失败：{done[1].content}")
        try:
            expression = sales_expression(done[0].content)
        except ValueError as exc:
            return _final(f"无法继续：{exc}")
        return _call(
            "把计算器返回的合计写入报告",
            "write_file",
            {
                "path": "report.md",
                "content": render_sales_report(expression, done[1].content),
            },
        )
    if len(done) == 3:
        if not done[2].ok:
            return _final(f"无法继续：写入报告失败：{done[2].content}")
        return _final("已根据计算器结果写入 report.md。\n合计：" + done[1].content.strip())
    return _final("无法继续：销售额任务的工具调用次数超出 Mock 计划。")


def _recovery(done: list[Message]) -> Decision:
    if not done:
        return _call(
            "先读取任务指定的文件",
            "read_file",
            {"path": "data/missing.txt"},
            plan=_PLANS["recovery"],
        )
    if len(done) == 1:
        if done[0].ok:
            return _final("无法继续：预期 data/missing.txt 不存在，但读取成功。")
        return _call("缺失文件失败后改为搜索 FIXME", "search_text", {"query": "FIXME"})
    if len(done) == 2:
        if not done[1].ok:
            return _final(f"无法继续：搜索 FIXME 失败：{done[1].content}")
        return _call("读取销售额数据", "read_file", {"path": "data/sales.txt"})
    if len(done) == 3:
        if not done[2].ok:
            return _final(f"无法继续：读取销售数据失败：{done[2].content}")
        try:
            expression = sales_expression(done[2].content)
        except ValueError as exc:
            return _final(f"无法继续：{exc}")
        return _call("计算销售额合计", "calculator", {"expression": expression})
    if len(done) == 4:
        if not done[3].ok:
            return _final(f"无法继续：计算失败：{done[3].content}")
        try:
            expression = sales_expression(done[2].content)
        except ValueError as exc:
            return _final(f"无法继续：{exc}")
        content = render_summary(done[0].content, done[1].content, expression, done[3].content)
        return _call("写入失败原因、FIXME 和销售额", "write_file", {"path": "summary.md", "content": content})
    if len(done) == 5:
        if not done[4].ok:
            return _final(f"无法继续：写入 summary.md 失败：{done[4].content}")
        return _final("已处理缺失文件失败，并根据工具结果写入 summary.md。")
    return _final("无法继续：恢复任务的工具调用次数超出 Mock 计划。")


def _blocked(user: str, done: list[Message]) -> Decision:
    if not done:
        if "非法算式" in user:
            return _call("尝试验证非法算式", "calculator", {"expression": "2+"}, plan=_PLANS["blocked"])
        return _call(
            "尝试读取 workspace 之外的文件",
            "read_file",
            {"path": "../secret.txt"},
            plan=_PLANS["blocked"],
        )
    if not done[-1].ok:
        return _final(f"无法继续：{done[-1].content}")
    return _final("无法继续：预期失败的工具调用却成功了，已停止。")


def _user_text(messages: list[Message]) -> str:
    for message in messages:
        if message.role == "user":
            return message.content
    return ""


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _call(thought: str, name: str, arguments: dict, plan: str | None = None) -> Decision:
    return Decision(thought=thought, tool_calls=[ToolCall(name=name, arguments=arguments)], plan=plan)


def _final(answer: str) -> Decision:
    return Decision(thought=answer, tool_calls=[], final_answer=answer)
