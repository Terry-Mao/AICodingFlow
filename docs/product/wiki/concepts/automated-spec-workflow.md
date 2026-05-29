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

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)

## Related Concepts

- [Issue ready label 与 agent assignment](issue-readiness-and-assignment.md)
- [Agent login 配置](agent-login-configuration.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
