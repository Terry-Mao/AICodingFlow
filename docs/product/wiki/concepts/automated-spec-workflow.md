---
type: concept
title: 自动 spec workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/spec-workflow.md
---

# 自动 spec workflow

自动 spec workflow 负责把准备进入规格设计阶段的 GitHub issue 派发给 Codex agent，并由外层 GitHub Actions 创建或更新 spec PR。

## 产品行为

- 普通新 issue 不会直接进入 spec 创建。
- workflow 支持手动触发，也支持 issue label、issue assignment 或 issue comment mention 触发。
- 自动事件只处理非 PR issue。
- issue 必须满足 `ready-to-spec` 与目标 agent assignment。
- 若 issue 已经带有 `ready-to-implement`，spec workflow 不启动，避免同一 issue 同时进入 spec 与 implementation 阶段。
- PR comment 不触发 spec workflow；PR comment mention 由 AI PR Review workflow 处理。

## Plan approval

- `plan-approved` 表示 spec PR 内容已批准，可作为 implementation workflow 的 authoritative spec context。
- `plan-approved` 不是 merge gate；spec PR 未 merge 时也可以被实现流程读取。
- approval workflow 会从 linked issue 移除 `ready-to-spec`，但不会自动添加 `ready-to-implement`。
- linked issue 已经同时带有 `ready-to-implement` 且 assign 给目标 agent 时，approval workflow 会触发 implementation workflow。
- 缺少 `ready-to-implement`、缺少目标 agent assignment 或无法解析 linked issue 时，只完成可执行的状态同步并跳过 implementation dispatch。

## PR 行为

- 创建或更新 spec PR 后不会自动触发 AI PR Review。
- 需要 review 时，在 open 且非 draft PR 的普通 conversation comment 中发送 `@AGENT_LOGIN /review`。
- 创建或更新 PR 时，workflow 只复用同一 head branch 上的 open PR，不把 closed PR 当作可更新目标。

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)

## Related Concepts

- [Issue ready label 与 agent assignment](issue-readiness-and-assignment.md)
- [Agent login 配置](agent-login-configuration.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
