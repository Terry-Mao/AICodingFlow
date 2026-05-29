---
type: summary
title: PR review verdict 与 non-member gate 摘要
sources:
  - docs/product/raw/pr-review-verdict.md
---

# PR review verdict 与 non-member gate 摘要

Source: [docs/product/raw/pr-review-verdict.md](../../raw/pr-review-verdict.md)

自动 PR review 将 `review-pr` / `review-spec` 产出的机器评审结论写入 `review.json.verdict`，发布流程再把该结论映射为 GitHub review event。`verdict` 是 Bot 的机器判断，不直接等同于 GitHub 的最终 merge gate。

## Review 输出契约

- `review.json` 必须包含 `verdict`、`body` 和 `comments`。
- `verdict` 只能是 `APPROVE` 或 `REJECT`。
- `APPROVE` 表示没有阻塞级发现。
- `REJECT` 表示存在需要修复后再合并的阻塞级发现。
- 建议和 nit 不应单独导致 `REJECT`。
- `recommended_reviewers` 仅用于需要推荐人工 reviewer 的场景，必须是字符串数组，最多包含 1 个 reviewer。

## PR 作者与类型

- `COLLABORATOR`、`MEMBER`、`OWNER` 视为 member / collaborator / owner。
- 其他非空、可识别身份在作者不是 bot 或 automation user 时视为 non-member。
- bot / automation user 不视为 non-member。
- `author_association` 缺失、为空或异常时采用保守行为，不视为 non-member。
- changed files 不全在 `specs/` 下时为 code PR。
- changed files 非空且全部路径以 `specs/` 开头时为 spec-only PR。
- spec-only PR 不进入 non-member blocking 或 reviewer request flow。

## Event 映射与 reviewer

- 只有 `non-member code PR + verdict = REJECT` 会发布 GitHub `REQUEST_CHANGES`。
- 其他场景默认发布 `COMMENT`。
- `non-member code PR + verdict = APPROVE` 时，workflow 尝试从 `.github/CODEOWNERS` 请求 1 个 human reviewer。
- 推荐 reviewer 必须是字符串、最多 1 个、不能是 PR 作者本人，并且必须出现在 `.github/CODEOWNERS`。
- 没有合格推荐时，workflow 使用 CODEOWNERS fallback。
- 没有可用 CODEOWNERS owner 时，不请求 reviewer，但 Bot review 发布仍可完成。

## Merge gate 语义

最终能否 merge 由 GitHub branch protection、required checks、code owner review、blocking `REQUEST_CHANGES` 和维护者权限共同决定。

## 支持的概念

- [PR review verdict](../concepts/pr-review-verdict.md)
- [Non-member gate 与 reviewer 请求](../concepts/non-member-gate-and-reviewer-request.md)
