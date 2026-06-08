---
type: concept
title: Create PR skill
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/create-pr-skill.md
---

# Create PR skill

`create-pr` skill 是本地 PR 创建与更新入口。它把当前已提交并已推送或可推送的工作分支整理成 review-ready PR，或更新当前分支上仍然 open 的既有 PR。

## 当前规则

- Skill 负责准备 PR 标题、正文、base/head 信息和 issue 关联。
- Skill 不负责实现代码、提交、推送分支或修改 GitHub issue。
- 只复用当前 head branch 上仍处于 open 状态的 PR。
- 已 merged 或 closed 的历史 PR 不可复用，也不应阻止同名分支创建新的 PR。
- 更新 open PR 前需要读取既有 PR body，并保留不明显属于 workflow 生成内容的人工补充。
- 没有当前分支 open PR 时创建新 PR。

## Supporting Summaries

- [Create PR skill 摘要](../summaries/create-pr-skill.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
