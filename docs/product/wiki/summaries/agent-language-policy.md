---
type: summary
title: Agent 输出语言策略摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/agent-language-policy.md
---

# Agent 输出语言策略摘要

Source: [docs/product/raw/agent-language-policy.md](../../raw/agent-language-policy.md)

AICodingFlow 的 agent-facing workflow 默认把人类可读输出写成中文，并优先跟随最强相关上下文的主要自然语言。最强上下文包括用户最新请求、issue 标题和正文、PR 或 spec 文本，以及正在编辑的既有文档。

## 语言选择规则

- 既有文档有明确语言时，编辑应保持该文档语言。
- 上下文混合或不明确时，默认使用中文。
- 语言策略只适用于人类可读内容；代码标识符、路径、label、branch name、API name、issue reference、命令、日志和引用输出保持原样。
- Workflow metadata 中的人类可读字段也适用该策略，例如 `pr_title`、`pr_summary` 和 `implementation_summary.md`。

## 集中管理

- 根目录 `AGENTS.md` 是仓库级 agent guidance 的权威入口，负责声明默认语言偏好。
- Skills 和 GitHub Actions prompt 应继承仓库级 guidance，不重复维护独立语言规则。

## 支持的概念

- [Agent 输出语言策略](../concepts/agent-language-policy.md)
