---
type: concept
title: AI PR Review workflow
sources:
  - docs/product/raw/pr-review-verdict.md
---

# AI PR Review workflow

AI PR Review 负责在 PR 满足可评审条件时运行机器评审，并根据 PR 类型选择仓库本地 review companion skill。

## 触发入口

- GitHub `pull_request` 事件可以触发 AI PR Review。
- `workflow_dispatch` 可以通过 PR number 手动触发 review。
- PR comment mention Actions variable `AGENT_LOGIN` 指定账号时，可以从 `issue_comment` 事件触发。
- 手动触发和 comment 触发会先解析目标 PR，再复用普通 PR 事件一致的 review 流程。

## Reviewable 条件

- 只有 open、非 draft 且 head repository 与当前仓库一致的 PR 会继续进入 AI review。
- closed PR、draft PR 或来自 fork 的 PR 会被跳过。
- 被跳过的 PR 不会运行 agent、发布 review 或上传 review artifact。

## Skill 选择

- spec-only PR 使用 `review-spec-repo`。
- 其他 code PR 使用 `review-pr-repo`。
- `review-pr-repo` 与 `review-spec-repo` 是仓库本地包装器，用于补充本仓库评审偏好，不改变核心输出契约。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [PR review verdict](pr-review-verdict.md)
- [Non-member gate 与 reviewer 请求](non-member-gate-and-reviewer-request.md)
- [本地 PR review 入口](local-pr-review-entrypoints.md)
