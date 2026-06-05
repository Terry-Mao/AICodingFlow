---
type: concept
title: Agent 输出语言策略
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/agent-language-policy.md
---

# Agent 输出语言策略

AICodingFlow 的 agent-facing workflow 默认把人类可读输出写成中文，并在具体任务中优先跟随最强相关上下文的主要自然语言。

## 适用范围

- 适用于 issue、PR 标题与正文、commit message summary、spec、review comments、状态报告、产品更新报告和 workflow metadata 等人类可读内容。
- Workflow metadata 中的 `pr_title`、`pr_summary`、`implementation_summary.md` 等人类可读字段同样适用。
- 代码标识符、路径、label、branch name、API name、issue reference、命令、日志和引用输出保持原样。

## 决策规则

- 优先跟随用户最新请求、issue 标题和正文、PR 或 spec 文本，以及正在更新的既有文档。
- 既有文档有明确语言时，编辑应保持该语言。
- 上下文混合或不明确时，默认使用中文。
- 根目录 `AGENTS.md` 集中声明仓库级默认语言偏好；skills 和 GitHub Actions prompt 继承该规则。

## Supporting Summaries

- [Agent 输出语言策略摘要](../summaries/agent-language-policy.md)
