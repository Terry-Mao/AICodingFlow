---
type: concept
title: PR review verdict
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/pr-review-verdict.md
---

# PR review verdict

`review.json.verdict` 是自动 PR review 的机器评审结论，由发布流程映射为 GitHub review event。它不直接等同于 GitHub 的最终 merge gate。

## 输出契约

- `review.json` 必须包含 `verdict`、`body` 和 `comments`。
- `verdict` 只能是 `APPROVE` 或 `REJECT`。
- `APPROVE` 表示没有阻塞级发现。
- `REJECT` 表示存在需要修复后再合并的阻塞级发现。
- 建议和 nit 不应单独导致 `REJECT`。
- `recommended_reviewers` 只用于需要推荐人工 reviewer 的场景，必须是字符串数组，最多 1 个 reviewer。

## Event 语义

- 只有 `non-member code PR + verdict = REJECT` 映射为 GitHub `REQUEST_CHANGES`。
- 其他场景默认发布 `COMMENT`。
- 最终 merge 仍由 GitHub branch protection、required checks、code owner review、blocking `REQUEST_CHANGES` 和维护者权限共同决定。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [Non-member gate 与 reviewer 请求](non-member-gate-and-reviewer-request.md)
- [本地 PR review 入口](local-pr-review-entrypoints.md)
