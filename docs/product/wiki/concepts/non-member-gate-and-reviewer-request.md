---
type: concept
title: Non-member gate 与 reviewer 请求
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/pr-review-verdict.md
---

# Non-member gate 与 reviewer 请求

Non-member gate 只对 code PR 的特定场景产生 blocking review event。Spec-only PR 不进入 non-member blocking 或 reviewer request flow。

## 作者身份

- `COLLABORATOR`、`MEMBER`、`OWNER` 视为 member / collaborator / owner。
- 其他非空、可识别身份在作者不是 bot 或 automation user 时视为 non-member。
- bot / automation user 不视为 non-member。
- `author_association` 缺失、为空或异常时采用保守行为，不视为 non-member。

## PR 类型

- code PR：changed files 不全在 `specs/` 下。
- spec-only PR：changed files 非空，且全部路径以 `specs/` 开头。
- spec-only PR 不进入 non-member blocking 或 reviewer request flow。

## Reviewer 请求

- `non-member code PR + verdict = APPROVE` 时，workflow 尝试请求 1 个 human reviewer。
- reviewer 来源限定为 `.github/CODEOWNERS`。
- agent 返回的 `recommended_reviewers` 必须是字符串数组，最多 1 个 reviewer。
- 推荐 reviewer 不能是 PR 作者本人，且必须出现在 `.github/CODEOWNERS`。
- 没有合格推荐时，workflow 使用 CODEOWNERS fallback。
- 没有可用 CODEOWNERS owner 时，不请求 reviewer，但 Bot review 发布仍可完成。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [PR review verdict](pr-review-verdict.md)
