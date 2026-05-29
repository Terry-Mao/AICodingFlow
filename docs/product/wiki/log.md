# Compile Log

## 2026-05-29

重新编译 `docs/product/raw/` 的权威产品文档，并校验现有 LLM Wiki 结构：

- 保持查询入口：[index.md](index.md) 与 [AGENTS.md](AGENTS.md)。
- 扩展 schema 文档：[schema/README.md](schema/README.md)、[schema/page-types.md](schema/page-types.md)、[schema/linking.md](schema/linking.md)、[schema/query.md](schema/query.md)、[schema/staging.md](schema/staging.md)。
- 为 summary 与 concept frontmatter 增加 `status`、`confidence`、`source_status`、`owner`、`last_reviewed` 和 `review_due`。
- 增加 Query 沉淀规则与暂存评审规则，避免未确认内容被写成当前事实。
- 校验 4 个 raw source 对应的 summary：
  - [summaries/spec-workflow.md](summaries/spec-workflow.md)
  - [summaries/implementation-workflow.md](summaries/implementation-workflow.md)
  - [summaries/pr-review-verdict.md](summaries/pr-review-verdict.md)
  - [summaries/product-change-reports.md](summaries/product-change-reports.md)
- 新增 2 个 PR review concept 页面：
  - [concepts/ai-pr-review-workflow.md](concepts/ai-pr-review-workflow.md)
  - [concepts/local-pr-review-entrypoints.md](concepts/local-pr-review-entrypoints.md)
- 校验 11 个 concept 页面，覆盖 workflow 触发、agent login、spec context、职责边界、AI PR Review 触发、本地 review、PR review verdict、non-member gate 和产品变更报告。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。
