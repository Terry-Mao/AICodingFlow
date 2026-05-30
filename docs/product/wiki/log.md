# Compile Log

## 2026-05-30

根据 `docs/product/raw/` 重新编译 wiki，并补齐新增 raw source 的查询链路：

- 新增 [本地 Git helper skills 摘要](summaries/local-git-helper-skills.md)，覆盖 `git-worktree` 的目录、分支、base、fetch、已有目标处理和安全边界。
- 新增 [本地 Git helper skills](concepts/local-git-helper-skills.md) concept，便于查询本地 Git 辅助能力的产品边界。
- 更新 [index.md](index.md)，链接新增 summary 与 concept。
- 校准 [PR review verdict 与 non-member gate 摘要](summaries/pr-review-verdict.md) 和 [本地 PR review 入口](concepts/local-pr-review-entrypoints.md)：本地 review 准备阶段支持已有 staged、unstaged 和未跟踪改动，并通过 `.local_review_baseline.status` 保护 review 阶段写入边界。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-05-29

重新编译 `docs/product/raw/` 的权威产品文档，并校验现有 LLM Wiki 结构：

- 保持查询入口：[index.md](index.md) 与 [AGENTS.md](AGENTS.md)。
- 扩展 schema 文档：[schema/README.md](schema/README.md)、[schema/page-types.md](schema/page-types.md)、[schema/linking.md](schema/linking.md)、[schema/query.md](schema/query.md)、[schema/staging.md](schema/staging.md)。
- 为 summary 与 concept frontmatter 增加 `status`、`confidence`、`source_status`、`owner`、`last_reviewed` 和 `review_due`。
- 增加 Query 沉淀规则与暂存评审规则，避免未确认内容被写成当前事实。
- 复核 `docs/product/raw/spec-workflow.md`，补充 spec approval 同步、implementation dispatch 条件、PR review 触发方式和 closed PR 不复用规则。
- 复核 `docs/product/raw/implementation-workflow.md`，补充 `pr-metadata.json` / `intended_files` 契约、workflow 文件 token 要求和 draft implementation PR 不自动 review 规则。
- 复核 `docs/product/raw/pr-review-verdict.md`，补充 comment command 精确匹配规则，并为缺失 frontmatter 的 PR review concept 页面补齐 linter 必需字段。
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
