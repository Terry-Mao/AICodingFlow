---
type: concept
title: Comment / manual review status
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-09
review_due: 2026-09-07
sources:
  - docs/product/raw/pr-review-verdict.md
---

# Comment / manual review status

AI PR Review 由 PR comment 或 `workflow_dispatch` 触发时，会为同仓库 head PR 补写 commit status，让该次 review run 出现在目标 PR 的 checks / statuses 视图中。

## 当前规则

- 只有目标 PR 的 head repository 是当前仓库时才写入 status。
- status context 为 `AI PR Review`。
- Review 运行开始时 status 为 `pending`。
- Review 运行结束后按 job 结果更新为 `success` 或 `failure`。
- status target URL 指向对应 GitHub Actions run。
- 该 status 让 CI dispatch、comment 或手动触发的 review run 出现在目标 PR 的 checks / statuses 视图中。
- AICodingFlow 参考 `CI` workflow 不再在测试前预写 `AI PR Review` status。
- 测试失败、测试被跳过或 dispatch 未发生时，参考 `CI` workflow 不写入该 status。
- 来自 fork 的 PR 不会写入该 status。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [PR review verdict](pr-review-verdict.md)
