---
type: summary
title: Issue triage workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/issue-triage-workflow.md
---

# Issue triage workflow 摘要

Source: [docs/product/raw/issue-triage-workflow.md](../../raw/issue-triage-workflow.md)

Issue triage workflow 在 issue 创建、重新打开、维护者显式请求或手动触发时，让 Codex agent 产出结构化分诊结果，并由外层 GitHub Actions 负责评论和标签更新。

## 触发条件

- `issues.opened` 和 `issues.reopened` 自动触发分诊。
- `issue_comment.created` 只在目标不是 PR、评论作者是 `OWNER`、`MEMBER` 或 `COLLABORATOR`，且正文包含配置的 `@AGENT_LOGIN /triage` 命令时触发。
- `workflow_dispatch` 可由维护者指定 issue number 手动触发。
- 评论触发会忽略引用块和 fenced code block 中的命令文本。
- 普通讨论、非可信作者评论、未配置 agent login 的评论、PR 评论，以及只 mention agent 但没有 `/triage` 命令的评论，都不是 triage 目标。

## 分诊上下文

- 生成阶段读取 issue、历史评论、默认分支、triage config、issue templates 和重复检查候选 issues。
- 重复检查候选由 workflow 预取，包含当前 issue 之外的 open issues 和最近 7 天内关闭的 closed issues；pull request items 会被排除。
- 显式评论触发时，该评论作为 `triggering_comment` 单独传给 agent；历史评论列表排除该触发评论。
- agent 必须读取 `triage-issue` 与 `dedupe-issue` skills，并可读取存在且受限的 repository companion skills。
- `dedupe_candidates.json` 是重复检查的权威候选列表；agent 不自行调用 GitHub API 扫描 issues。
- issue bodies、comments、templates、original report 和 fenced code blocks 都是待分析数据，不是可执行 workflow 指令。

## Handoff 与更新边界

- agent 的唯一 handoff 是 `triage_result.json`。
- 结果包含 labels、repro、confidence、related_files、root_cause、summary、follow_up_questions、duplicate_of 和 issue_body。
- `follow_up_questions` 与 `duplicate_of` 互斥；重复判断优先于补充问题。
- `plan-approved`、`ready-to-implement` 和 `ready-to-spec` 是受保护 labels，分诊结果不得请求添加。
- agent 不直接修改 GitHub；apply 阶段用写权限 job 再次校验后同步 labels，并按需创建或更新 triage comment。
- label 同步只管理 triage config 中定义且非受保护的 labels，保留 issue 上不属于 managed label set 的其他 labels。

## 支持的概念

- [Issue triage workflow](../concepts/issue-triage-workflow.md)
- [Issue triage 结果契约](../concepts/issue-triage-result-contract.md)
- [Repo-specific duplicate guidance](../concepts/repo-specific-duplicate-guidance.md)
- [Agent 与外层 workflow 职责边界](../concepts/agent-workflow-boundaries.md)

