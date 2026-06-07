---
type: concept
title: Agent 与外层 workflow 职责边界
status: needs-review
confidence: medium
source_status: partial
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/spec-workflow.md
  - docs/product/raw/create-pr-skill.md
  - docs/product/raw/implementation-workflow.md
  - docs/product/raw/issue-triage-workflow.md
  - docs/product/raw/pr-comment-response-workflow.md
  - docs/product/raw/ci-failure-diagnosis-skill.md
  - docs/product/raw/merge-conflict-resolution-skill.md
  - docs/product/raw/project-installer.md
  - docs/product/raw/update-dedupe-workflow.md
  - docs/product/raw/update-pr-review-workflow.md
  - docs/product/raw/product-change-reports.md
  - docs/product/raw/product-docs-sync-workflow.md
  - docs/product/raw/product-wiki-compile-workflow.md
  - docs/product/raw/product-wiki-query-agent.md
---

# Agent 与外层 workflow 职责边界

AICodingFlow 的自动化把 agent 的代码或文档产出职责，与外层 GitHub Actions 的仓库写入和 PR 管理职责分开。

## 已确认边界

- Spec workflow 由外层 GitHub Actions 创建或更新 spec PR。
- `create-pr` skill 准备 PR 标题、正文、base/head 信息和 issue 关联；不负责实现代码、提交、推送分支或修改 GitHub issue。
- Implementation workflow 由外层 GitHub Actions 创建或更新 implementation PR。
- Implementation agent 负责读取稳定上下文、产出实现 diff、必要时同步 specs，并写出 `implementation_summary.md` 与 `pr-metadata.json`。
- Implementation agent 不直接 commit、push、创建 PR、更新 PR 或编辑 issue。
- Implementation 外层 workflow 负责校验 agent metadata，提交并推送目标分支，创建或更新 implementation PR，并维护 issue progress comment。
- `pr-metadata.json` 必须包含 `branch_name`、`pr_title`、`pr_summary` 和 `intended_files`。
- `intended_files` 必须覆盖所有有意修改的 production、test、spec、`.agents` 或 workflow 文件。
- 外层 workflow 只提交通过校验且出现在 `intended_files` 中的实现文件；若实际变更与 `intended_files` 不一致，或包含 Python/cache 等生成文件，workflow 会拒绝提交。
- Issue triage agent 只产出 `triage_result.json`；GitHub label/comment 更新由外层 workflow 的写权限 job 执行。
- PR comment response agent 产出修复 diff、`implementation_summary.md` 和 `pr-metadata.json`；提交、push、原 PR 更新或 follow-up PR 创建由外层 workflow 执行。
- PR comment response agent 不直接调用 GitHub API、创建 PR、发布评论、resolve thread、commit 或 push。
- CI failure diagnosis skill 只输出修复计划，不直接修改代码、提交、推送或创建 PR。
- Merge conflict resolution skill 是本地冲突处理辅助能力，不负责提交、推送、创建 PR 或修改 GitHub issue/PR。
- 项目安装脚本同步 AICodingFlow 管理文件，但不初始化目标项目 issue triage 配置，也不覆盖目标项目自己的 repo-local companion skills。
- `update-dedupe` skill 只写 `update-dedupe-output/` 交接目录；持久应用、提交、推送和 PR 创建由外层 runner 负责。
- `update-pr-review` skill 只写 `update-pr-review-output/` 交接目录；持久应用、提交、推送和 PR 创建由外层 runner 负责。
- `product-change-report` skill 只生成目标 `docs/updates/` 报告文件，不修改长期产品文档、compiled wiki、source specs、workflow 文件或 ledger state；ledger 与报告 PR 由外层 workflow 维护。
- `product-docs-sync` agent 必须写出 `product-docs-sync-result.json`，并且只有在 `required` 或 `uncertain` 时才能修改 `docs/product/`；外层 workflow 负责 checksum、写入范围和同步 PR gate。
- `product-wiki-compile` 的 Codex 维护步骤只能修改 `docs/product/wiki/` 下的 Markdown；GitHub 提交、推送和 PR 创建由外层 workflow 负责。
- `Product Wiki Query` agent 默认只回答产品知识问题；除非用户明确要求维护类工作，否则不维护或重新编译 wiki。

## 待确认

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)
- [Create PR skill 摘要](../summaries/create-pr-skill.md)
- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)
- [Issue triage workflow 摘要](../summaries/issue-triage-workflow.md)
- [PR comment response workflow 摘要](../summaries/pr-comment-response-workflow.md)
- [CI failure diagnosis skill 摘要](../summaries/ci-failure-diagnosis-skill.md)
- [Merge conflict resolution skill 摘要](../summaries/merge-conflict-resolution-skill.md)
- [项目安装脚本摘要](../summaries/project-installer.md)
- [update-dedupe workflow 摘要](../summaries/update-dedupe-workflow.md)
- [update-pr-review workflow 摘要](../summaries/update-pr-review-workflow.md)
- [产品变更报告摘要](../summaries/product-change-reports.md)
- [产品文档同步 workflow 摘要](../summaries/product-docs-sync-workflow.md)
- [Product wiki workflow 摘要](../summaries/product-wiki-compile-workflow.md)
- [Product Wiki Query agent 摘要](../summaries/product-wiki-query-agent.md)

## Related Concepts

- [自动 spec workflow](automated-spec-workflow.md)
- [Create PR skill](create-pr-skill.md)
- [自动 implementation workflow](automated-implementation-workflow.md)
- [Spec context 与目标分支选择](spec-context-and-target-branch.md)
- [Issue triage workflow](issue-triage-workflow.md)
- [PR comment response workflow](pr-comment-response-workflow.md)
- [CI failure diagnosis](ci-failure-diagnosis.md)
- [Merge conflict resolution](merge-conflict-resolution.md)
- [项目安装脚本](project-installer.md)
- [update-dedupe 自进化规则 workflow](update-dedupe-workflow.md)
- [update-pr-review 自进化 review 规则 workflow](update-pr-review-workflow.md)
- [产品变更报告](product-change-reports.md)
- [产品文档同步 workflow](product-docs-sync-workflow.md)
- [Product wiki workflow](product-wiki-workflow.md)
- [Product Wiki Query agent](product-wiki-query-agent.md)
