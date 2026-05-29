---
type: concept
title: Spec context 与目标分支选择
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/implementation-workflow.md
---

# Spec context 与目标分支选择

Implementation workflow 按固定优先级选择实现上下文和目标分支。

## 选择顺序

1. 存在带 `plan-approved` 的 spec PR 时，使用该 PR 的 head branch 作为目标分支，并把实现追加到同一个 PR 分支。
2. 没有 approved spec PR，但默认分支存在 `specs/issue-<issue-number>/` 下的 spec 时，使用默认分支 spec 作为上下文，目标分支默认为 `spec/implement-issue-<issue_number>`。
3. 没有任何 spec context 时，workflow 仍可启动实现，但 agent prompt 必须明确说明没有 approved 或 repository spec context。
4. 存在未批准 spec PR 且默认分支没有 specs 时，workflow 不启动实现，并在 progress comment 中说明没有可用的 approved spec context。

## Draft implementation PR

当没有 approved spec PR 时，workflow 可以创建新的 draft implementation PR，也可以更新已有 draft implementation PR。

## Supporting Summaries

- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [自动 implementation workflow](automated-implementation-workflow.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
