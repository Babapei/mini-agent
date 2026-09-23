# 汇总报告

## 1. 读取失败原因
- 读取 `data/missing.txt` 失败：文件不存在（工具返回：文件不存在：data/missing.txt）。

## 2. workspace 中的 FIXME
- `docs/design.md:6` - FIXME: 运费未计入
- `src/order.ts:4` - FIXME: 没有处理空数组

（另：`todo-report.md:30` 提到同一搜索发现 docs/design.md:6 的 FIXME，因不属于 TODO 未计入其报告，此处仍作为 FIXME 命中列出。）

## 3. 销售额
数据来源：`data/sales.txt`

| 产品 | 数量 | 单价 | 小计 |
| --- | --- | --- | --- |
| Pen | 2 | 10.5 | 21 |
| Notebook | 3 | 20 | 60 |
| Paper | 4 | 5 | 20 |

计算式：2*10.5 + 3*20 + 4*5 = 101

所有产品销售额之和：101
