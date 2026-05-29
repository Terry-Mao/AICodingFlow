---
type: concept
title: Issue ready label 与 agent assignment
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/spec-workflow.md
  - docs/product/raw/implementation-workflow.md
---

# Issue ready label 与 agent assignment

Issue 不会仅因新建而进入自动 spec 或 implementation 阶段。自动派发要求 issue 不是 PR，并且 ready label 与目标 agent assignment 同时满足。

## Spec 阶段

- `ready-to-spec` label 新增时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-spec` label。
- comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。
- 手动触发同样必须满足 `ready-to-spec` 与目标 agent assignment。
- issue 已带 `ready-to-implement` 时，spec workflow 不启动。
- spec PR 获得 `plan-approved` 后，approval workflow 会从 linked issue 移除 `ready-to-spec`，但不会自动添加 `ready-to-implement`。

## Implementation 阶段

- `ready-to-implement` label 新增时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-implement` label。
- comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。
- `plan-approved` label 只影响 spec context 可用性，不单独触发 implementation workflow。
- 只有 linked issue 已经带有 `ready-to-implement` 且 assign 给目标 agent 时，plan approval 同步流程才会 dispatch implementation workflow。

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)
- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [Agent login 配置](agent-login-configuration.md)
- [自动 spec workflow](automated-spec-workflow.md)
- [自动 implementation workflow](automated-implementation-workflow.md)
