# Product Wiki Agent Guide

本目录是由 `docs/product/raw/` 编译出的 LLM Wiki。只有 `docs/product/wiki/**/*.md` 属于编译 wiki；`docs/product/raw/` 仍是产品事实的权威来源。

## 查询顺序

1. 从 [index.md](index.md) 开始，按产品区域或 workflow 找到相关页面。
2. 优先打开最相关的 concept 页面，理解稳定规则、状态和边界。
3. 从 concept 页面继续打开 supporting summaries，查看该概念由哪些源摘要支持。
4. 当需要精确事实、来源措辞或冲突判断时，从 summary 的 `sources` 回到 `docs/product/raw/`。
5. 如果 wiki 与 raw 冲突，以 raw 为准，并更新 wiki 或将事实标记为 `待确认` / `开放问题`。
6. 如果一次查询暴露出可复用的长期知识缺口，优先更新相关 summary/concept；无法确认时按 [暂存评审](schema/staging.md) 记录，不要把未确认内容写成当前事实。

## 编辑要求

- 优先沿现有链接遍历，避免只依赖宽泛关键词搜索。
- 编辑 summary 或 concept 时保留 YAML frontmatter，并维护 `sources`。
- summary 和 concept 的 frontmatter 必须维护 `status`、`confidence`、`source_status`、`owner`、`last_reviewed`、`review_due`。
- 新增概念必须从 concept 链接到支持它的 summary；summary 也必须反向链接到相关 concept。
- 不要把计划、推测或已被 raw 反驳的行为写成当前产品事实。
- 对无法从 raw 确认的内容使用 `待确认` 或 `开放问题`，并放在专门章节中供 PR review 处理。
