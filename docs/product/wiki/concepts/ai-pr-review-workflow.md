---
type: concept
title: AI PR Review workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-09
review_due: 2026-09-07
sources:
  - docs/product/raw/pr-review-verdict.md
---

# AI PR Review workflow

AI PR Review 负责在 PR 满足可评审条件时运行机器评审，并根据 PR 类型选择仓库本地 review companion skill。

## 触发入口

- AI PR Review 可由 `pull_request_target` 在同仓库 PR 的 opened、reopened、synchronize、ready_for_review 事件触发，也可由目标项目 CI 成功路径通过 `workflow_dispatch` 输入 PR number 触发。
- 目标项目已有自己的 CI 时，应在自己的 CI 成功路径中 dispatch `review-pr.yml`，而不是修改已安装的 `review-pr.yml`。
- `workflow_dispatch` 可以通过 PR number 手动触发 review。
- PR conversation comment mention Actions variable `AGENT_LOGIN` 指定账号时，可以从 `issue_comment` 事件触发。
- `review-pr.yml` 不监听 GitHub `pull_request` 事件；自动 `pull_request_target` 入口会被触发器门控和 resolver 双重限制为同仓库 head，维护者仍可通过 `workflow_dispatch` 显式评审 fork PR。
- 手动触发和 comment 触发会先解析目标 PR，再复用 review 流程。
- `workflow_dispatch` 触发允许 `github-actions[bot]` 运行 Codex review action；使用 GitHub App token、PAT 或第三方 CI dispatch 时，bot allowlist 需要匹配实际触发 actor，或改用有人类账号权限的 token 触发。
- Comment 触发要求 `@AGENT_LOGIN /review` 独占一行，允许前后空白。
- 裸 `/review`、单纯 `@AGENT_LOGIN` mention、quoted line、fenced code block、普通句子中的提及，以及带额外参数的 `@AGENT_LOGIN /review ...` 都不会触发 AI review。
- 普通 issue comment 和 PR inline review comment 不是该入口。

## Reviewable 条件

- 自动 `pull_request_target` 入口只有 open、非 draft 且 head repository 与当前仓库一致的 PR 会继续进入 AI review；`workflow_dispatch` 和有效 comment 入口可显式评审 fork PR。
- closed PR 或 draft PR 会被跳过。
- 被跳过的 PR 不会运行 agent、发布 review 或上传 review artifact。

## Skill 选择

- spec-only PR 主入口使用 `review-spec`。
- 其他 code PR 主入口使用 `review-pr`。
- review workspace 会复制 `.github/skills/` 与 `.agents/contracts/`，其中 `.agents/contracts/review.md` 是共享 review contract。
- `review-pr` 与 `review-spec` 会读取对应的 `review-pr-repo` 或 `review-spec-repo` companion，用于补充本仓库评审偏好，不改变共享输出契约。
- Code PR review 会应用 `security-review-pr` 补充安全检查。
- Spec-only PR review 会应用 `security-review-spec` 补充设计层安全检查。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [Comment / manual review status](comment-manual-review-status.md)
- [安全补充 review](security-review-supplements.md)
- [PR review verdict](pr-review-verdict.md)
- [Non-member gate 与 reviewer 请求](non-member-gate-and-reviewer-request.md)
- [本地 PR review 入口](local-pr-review-entrypoints.md)
