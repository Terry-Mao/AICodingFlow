---
type: concept
title: Agent 与外层 workflow 职责边界
status: needs-review
confidence: medium
source_status: partial
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/spec-workflow.md
  - docs/product/raw/implementation-workflow.md
---

# Agent 与外层 workflow 职责边界

AICodingFlow 的自动化把 agent 的代码或文档产出职责，与外层 GitHub Actions 的仓库写入和 PR 管理职责分开。

## 已确认边界

- Spec workflow 由外层 GitHub Actions 创建或更新 spec PR。
- Implementation workflow 由外层 GitHub Actions 创建或更新 implementation PR。
- Implementation agent 负责读取稳定上下文、产出实现 diff、必要时同步 specs，并写出 `implementation_summary.md` 与 `pr-metadata.json`。
- Implementation agent 不直接 commit、push、创建 PR、更新 PR 或编辑 issue。
- Implementation 外层 workflow 负责校验 agent metadata，提交并推送目标分支，创建或更新 implementation PR，并维护 issue progress comment。
- `pr-metadata.json` 必须包含 `branch_name`、`pr_title`、`pr_summary` 和 `intended_files`。
- `intended_files` 必须覆盖所有有意修改的 production、test、spec、`.agents` 或 workflow 文件。
- 外层 workflow 只提交通过校验且出现在 `intended_files` 中的实现文件；若实际变更与 `intended_files` 不一致，或包含 Python/cache 等生成文件，workflow 会拒绝提交。

## 待确认

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)
- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [自动 spec workflow](automated-spec-workflow.md)
- [自动 implementation workflow](automated-implementation-workflow.md)
- [Spec context 与目标分支选择](spec-context-and-target-branch.md)
