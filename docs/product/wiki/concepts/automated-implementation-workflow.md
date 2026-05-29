---
type: concept
title: 自动 implementation workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-29
review_due: 2026-08-27
sources:
  - docs/product/raw/implementation-workflow.md
---

# 自动 implementation workflow

自动 implementation workflow 负责把已经准备实现的 GitHub issue 派发给 Codex agent，并由外层 GitHub Actions 创建或更新 implementation PR。

## 产品行为

- 普通新 issue 不会直接进入实现阶段。
- workflow 支持手动触发，也支持 issue label、issue assignment 或 issue comment mention 触发。
- 自动事件只处理非 PR issue。
- issue 必须满足 `ready-to-implement` 与目标 agent assignment。
- Spec PR 的 `plan-approved` label 只表示该 PR 可作为实现上下文，不会单独触发 implementation workflow。

## Supporting Summaries

- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [Issue ready label 与 agent assignment](issue-readiness-and-assignment.md)
- [Agent login 配置](agent-login-configuration.md)
- [Spec context 与目标分支选择](spec-context-and-target-branch.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
