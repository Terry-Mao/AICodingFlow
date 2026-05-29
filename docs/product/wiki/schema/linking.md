# Linking Rules

## 查询链路

推荐链路是：

1. [../index.md](../index.md)
2. `concepts/*.md`
3. `summaries/*.md`
4. `../raw/*.md`

## 链接要求

- index 必须链接所有 summary、concept、schema、AGENTS 和 log 页面。
- summary 必须链接它支持的 concept 页面。
- concept 必须链接 supporting summary 页面。
- schema 页面必须覆盖页面类型、链接规则、查询流程和暂存评审规则。
- wiki 内部链接使用相对 Markdown 链接，例如 `[自动 spec workflow](../concepts/automated-spec-workflow.md)`。
- raw source 链接也使用相对路径，例如 `[docs/product/raw/spec-workflow.md](../../raw/spec-workflow.md)`。

## 来源追溯

每个 concept 的事实应能追溯到：

- concept frontmatter 的 `sources`。
- concept 内的 supporting summaries。
- summary frontmatter 的 `sources`。
- summary 内的 raw source 链接。
