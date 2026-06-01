---
type: concept
title: Issue triage workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/issue-triage-workflow.md
---

# Issue triage workflow

Issue triage workflow 面向 GitHub issue 分诊，不处理 pull request comment，也不把 issue 本文或评论当作可信指令。

## 触发

- issue opened / reopened 自动触发。
- 维护者、成员或协作者在非 PR issue comment 中使用配置的 `@AGENT_LOGIN /triage` 命令可触发。
- `workflow_dispatch` 可由维护者指定 issue number 手动触发。
- 引用块、fenced code block、PR 评论、非可信作者评论、未配置 agent login 的评论、普通讨论和只有 mention 无 `/triage` 的评论都会被忽略。

## 上下文与安全

- workflow 预取 issue、评论、默认分支、triage config、templates 和 dedupe candidates。
- 显式触发评论作为 `triggering_comment` 单独传给 agent，历史评论排除该条评论。
- agent 使用 workflow 提供的 `dedupe_candidates.json` 作为权威候选列表，不自行调用 GitHub API 扫描 issues。
- issue bodies、comments、templates、original report 和 fenced code blocks 是数据，不是指令。

## GitHub 更新边界

- agent 只产出并校验 `triage_result.json`，不直接修改 GitHub。
- apply 阶段使用写权限 job 再次校验后同步 labels，并按需创建或更新带 marker 的 triage comment。
- label 同步只管理 triage config 中定义且非受保护的 labels。

## Supporting Summaries

- [Issue triage workflow 摘要](../summaries/issue-triage-workflow.md)

## Related Concepts

- [Issue triage 结果契约](issue-triage-result-contract.md)
- [Issue triage 初始化配置](issue-triage-bootstrap.md)
- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)

