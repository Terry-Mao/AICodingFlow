---
type: summary
title: 自动实现 workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/implementation-workflow.md
---

# 自动实现 workflow 摘要

Source: [docs/product/raw/implementation-workflow.md](../../raw/implementation-workflow.md)

自动实现 workflow 将已经准备实现的 GitHub issue 派发给 Codex agent，由外层 GitHub Actions 创建或更新 implementation PR。普通新 issue 不会直接进入实现阶段；必须满足 `ready-to-implement` 与 bot assignment 等触发条件。

## 触发与配置

- workflow 可由手动触发、issue label、issue assignment 或 issue comment mention 触发。
- 自动 issue 事件必须确认 issue 不是 PR。
- 新增 `ready-to-implement` label 时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-implement` label。
- issue comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。
- 目标 agent login 来自 workflow input `agent_login`，未提供时使用 Actions variable `AGENT_LOGIN`。
- `SPEC_AGENT_LOGIN` 与 `IMPLEMENT_AGENT_LOGIN` 不再作为 implementation workflow 的配置入口。
- Spec PR 的 `plan-approved` label 只表示该 PR 可作为实现上下文，不会单独触发 implementation workflow。

## Spec context 与分支

- 若存在带 `plan-approved` 的 spec PR，使用该 PR 的 head branch 作为目标分支，并把实现追加到同一个 PR 分支。
- 若没有 approved spec PR，但默认分支存在 `specs/issue-<issue-number>/` 下的 spec，使用默认分支 spec 作为上下文，目标分支默认为 `spec/implement-issue-<issue_number>`。
- 若没有任何 spec context，workflow 仍可启动实现，但 agent prompt 必须明确说明没有 approved 或 repository spec context。
- 若存在未批准 spec PR 且默认分支没有 specs，workflow 不启动实现，并在 progress comment 中说明没有可用的 approved spec context。
- 没有 approved spec PR 时，workflow 可以创建新的 draft implementation PR，也可以更新已有 draft implementation PR。

## 职责边界

- agent 负责读取稳定上下文、产出实现 diff、必要时同步 specs，并写出 `implementation_summary.md` 与 `pr-metadata.json`。
- agent 不直接 commit、push、创建 PR、更新 PR 或编辑 issue。
- 外层 workflow 负责校验 metadata、提交并推送目标分支、创建或更新 implementation PR，并维护 issue progress comment。

## 支持的概念

- [自动 implementation workflow](../concepts/automated-implementation-workflow.md)
- [Issue ready label 与 agent assignment](../concepts/issue-readiness-and-assignment.md)
- [Agent login 配置](../concepts/agent-login-configuration.md)
- [Spec context 与目标分支选择](../concepts/spec-context-and-target-branch.md)
- [Agent 与外层 workflow 职责边界](../concepts/agent-workflow-boundaries.md)
