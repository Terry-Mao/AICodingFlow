---
type: concept
title: PR comment response 分支策略
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/pr-comment-response-workflow.md
---

# PR comment response 分支策略

`respond-to-pr-comment` workflow 根据授权和写入能力选择修复写入位置。

## 策略

- `push-head`：触发者已授权，且 workflow token 能写 PR head branch；修复提交到原 PR head branch。
- `fallback-pr-to-fork`：触发者已授权，但不能写原 PR head branch，且可以写 base repo；workflow 基于原 PR head commit 创建 `spec/respond-pr-<pr_number>` 前缀 fallback branch，再创建或更新 follow-up PR。
- `blocked`：触发者已授权，但既不能写 head branch 也不能写 fallback branch；workflow 不运行 agent 修改代码，并输出可诊断原因。
- 未授权触发者不会进入写入分支策略，应在 context 阶段以 `should_run = false` 跳过。

## 输出约束

- `pr-metadata.json.branch_name` 必须等于 context 中允许的 `agent_push_branch`。
- `intended_files` 必须覆盖所有应提交文件，不能包含 handoff、日志或缓存文件。
- `push-head` 成功后不会按 metadata 改写原 PR title/body。
- fallback PR body 会说明来源 PR 和触发评论。

## Supporting Summaries

- [PR comment response workflow 摘要](../summaries/pr-comment-response-workflow.md)

## Related Concepts

- [PR comment response workflow](pr-comment-response-workflow.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)

