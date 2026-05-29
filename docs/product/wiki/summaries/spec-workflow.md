---
type: summary
title: 自动 spec workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/spec-workflow.md
---

# 自动 spec workflow 摘要

Source: [docs/product/raw/spec-workflow.md](../../raw/spec-workflow.md)

自动 spec workflow 将准备进入规格设计阶段的 GitHub issue 派发给 Codex agent，由外层 GitHub Actions 创建或更新 spec PR。普通新 issue 不会直接进入 spec 创建；必须先满足 ready label 与目标 agent 触发条件。

## 关键规则

- workflow 可由手动触发、issue label、issue assignment 或 issue comment mention 触发。
- 自动 issue 事件必须确认 issue 不是 PR。
- 新增 `ready-to-spec` label 时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-spec` label。
- issue comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。
- 目标 agent login 来自 workflow input `agent_login`，未提供时使用 Actions variable `AGENT_LOGIN`。
- `SPEC_AGENT_LOGIN` 不再作为 spec workflow 的配置入口。
- 手动触发也必须满足 `ready-to-spec` 与目标 agent assignment。
- 如果 issue 已经带有 `ready-to-implement`，spec workflow 不启动，避免同一 issue 同时进入 spec 与 implementation 阶段。
- PR comment 不触发 spec workflow；PR comment mention 由 AI PR Review workflow 处理。

## Plan approval 与后续 review

- 维护者在 spec PR 上添加 `plan-approved` label 表示该 plan 已批准，可作为 implementation workflow 的 authoritative spec context。
- `plan-approved` 不是 merge gate；未 merge 的 spec PR 也可被 implementation workflow 读取。
- approval workflow 会解析 linked issue，并自动从该 issue 移除 `ready-to-spec`；如果原本没有该 label，视为幂等成功。
- approval workflow 不会自动添加 `ready-to-implement`。
- linked issue 已同时带有 `ready-to-implement` 且 assign 给目标 agent 时，approval workflow 会在移除 `ready-to-spec` 后触发 implementation workflow。
- 缺少 `ready-to-implement`、缺少目标 agent assignment 或无法解析 linked issue 时，只完成可执行的状态同步并跳过 implementation dispatch。
- 创建或更新 spec PR 后不会自动触发 AI PR Review；需要 review 时，在 open 且非 draft PR 的普通 conversation comment 中发送 `@AGENT_LOGIN /review`。
- 创建或更新 PR 时，workflow 只复用同一 head branch 上的 open PR，不把 closed PR 当作可更新目标。

## 支持的概念

- [自动 spec workflow](../concepts/automated-spec-workflow.md)
- [Issue ready label 与 agent assignment](../concepts/issue-readiness-and-assignment.md)
- [Agent login 配置](../concepts/agent-login-configuration.md)
- [Agent 与外层 workflow 职责边界](../concepts/agent-workflow-boundaries.md)
