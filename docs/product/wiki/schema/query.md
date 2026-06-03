# Query Workflow

查询 wiki 时优先走链接图，而不是只做宽泛关键词搜索。

## 查询步骤

1. 从 [../index.md](../index.md) 进入，找到最接近问题的 concept 或 summary。
2. 优先阅读 concept，确认当前规则、状态、边界和相关页面。
3. 沿 concept 的 supporting summaries 回到 source summary。
4. 当答案涉及精确规则、冲突判断、权限边界或 reviewer 可争议事实时，从 summary 的 `sources` 回到 `docs/product/raw/`。
5. 回答时区分已确认事实、推断和 `待确认` / `开放问题`。

## 查询后沉淀

- 如果问题暴露出 wiki 已有事实但链接不足，更新链接或 index 分组。
- 如果答案是长期产品知识且 raw source 已支持，更新相关 summary/concept。
- 如果答案有价值但 raw source 不足，按 [staging.md](staging.md) 进入暂存评审。
- 临时排查、一次性命令输出、未合并实现细节不写入 wiki。

## 待确认 / 开放问题

- 当前无本查询流程说明自身的待确认项。
