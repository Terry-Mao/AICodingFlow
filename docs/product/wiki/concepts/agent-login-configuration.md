---
type: concept
title: Agent login 配置
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

# Agent login 配置

Spec 与 implementation workflow 都使用同一套目标 agent login 配置规则：优先读取 workflow input `agent_login`，未提供时使用仓库 Actions variable `AGENT_LOGIN`。

## 当前规则

- `SPEC_AGENT_LOGIN` 不再作为 spec workflow 的配置入口。
- `SPEC_AGENT_LOGIN` 与 `IMPLEMENT_AGENT_LOGIN` 不再作为 implementation workflow 的配置入口。
- ready label 与 assignment 判断都围绕目标 agent login 执行。

## Supporting Summaries

- [自动 spec workflow 摘要](../summaries/spec-workflow.md)
- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [Issue ready label 与 agent assignment](issue-readiness-and-assignment.md)
- [自动 spec workflow](automated-spec-workflow.md)
- [自动 implementation workflow](automated-implementation-workflow.md)
