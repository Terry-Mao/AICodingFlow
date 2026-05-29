# Wiki Schema

本 schema 描述 `docs/product/wiki/` 的编译结构。raw 文档仍是权威来源，wiki 页面用于更快查询、跨源聚合和来源追溯。

## 必需结构

- [../AGENTS.md](../AGENTS.md): 后续 agent 的查询与编辑指南。
- [../index.md](../index.md): wiki 第一入口，链接所有 summary、concept、schema 和 log 页面。
- [../summaries/](../summaries/): 每个有意义 raw 产品文档对应一个 source summary。
- [../concepts/](../concepts/): 可直接查询的产品概念、workflow、规则、状态和边界。
- [../log.md](../log.md): 本次编译变更、开放问题和待确认事项。

## 约束

- wiki 文件只使用 Markdown。
- summary 与 concept 页面必须包含 YAML frontmatter。
- wiki 内部链接必须使用相对 Markdown 链接。
- 不确定或冲突信息必须标记为 `待确认` 或 `开放问题`。

更多细节见 [page-types.md](page-types.md) 与 [linking.md](linking.md)。
