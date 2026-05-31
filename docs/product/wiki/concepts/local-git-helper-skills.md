---
type: concept
title: 本地 Git helper skills
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-30
review_due: 2026-08-28
sources:
  - docs/product/raw/local-git-helper-skills.md
---

# 本地 Git helper skills

本地 Git helper skills 是仓库内的开发辅助能力，用于帮助 agent 执行 Git 准备动作，同时保护用户工作区和远端状态。

## 产品边界

- 本地 Git helper skills 不会自动提交、推送、删除分支或修改 GitHub issue/PR。
- `git-worktree` 用于为并行分支工作创建独立的本地 worktree。
- 默认 worktree 目录为 `.worktrees/<branch-slug>`；该目录被仓库忽略，避免误进入 Git、review 或提交流程。
- 当前 worktree 有未提交改动时，创建新 worktree 可以继续，但必须说明这些改动不会被复制到新 worktree。
- 若目标 branch、worktree 或目录已存在，helper 只报告现有路径并停止，不覆盖、不删除、不 prune、不强制复用。

## 分支与 base 规则

- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 自定义分支保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。
- 默认 base ref 按 `upstream/main`、`origin/main`、`main` 的顺序选择。
- 有 remote 且网络可用时，helper 在检查 base 是否最新前运行 `git fetch`；无法 fetch 时必须说明 base freshness 未验证。

## Supporting Summaries

- [本地 Git helper skills 摘要](../summaries/local-git-helper-skills.md)

## Related Concepts

- [本地 PR review 入口](local-pr-review-entrypoints.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
