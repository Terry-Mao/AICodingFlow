---
type: concept
title: 本地 Git helper skills
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/local-git-helper-skills.md
---

# 本地 Git helper skills

本地 Git helper skills 是仓库内的开发辅助能力，用于帮助 agent 执行 Git 准备动作，同时保护用户工作区和远端状态。

## 产品边界

- 本地 Git helper skills 不会自动提交、推送、删除分支或修改 GitHub issue/PR。
- `git-branch` 用于创建符合仓库命名和 base 分支安全规则的本地工作分支。
- `git-worktree` 用于为并行分支工作创建独立的本地 worktree。
- 默认 worktree 目录为 `.worktrees/<branch-name>`，保留分支名中的目录层级；该目录被仓库忽略，避免误进入 Git、review 或提交流程。
- 当前 worktree 有未提交改动时，创建新 worktree 可以继续，但必须说明这些改动不会被复制到新 worktree。
- 若目标 branch、worktree 或目录已存在，helper 只报告现有路径并停止，不覆盖、不删除、不 prune、不强制复用。
- `git-commit` 只 stage 目标文件并使用普通 `git commit -m`，hook 失败时停止。
- `git-push` 只在用户要求 push 或 publish 且已有 commit 时发布本地工作。

## 分支与 base 规则

- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 非 issue 分支使用 `<type>/<user-provided-name>`，不会凭空补 issue ID。
- worktree 自定义分支保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。
- 同一仓库内开发默认优先使用 `origin/<base>`，其次使用本地 `<base>`；只在 fork 工作流或仓库明确要求时使用 `upstream/<base>`。
- 默认 base 是 `main`；远端分支冲突、fetch 和 base freshness 只有影响结果时才检查。
- 从远端 base 创建分支或 worktree 时使用 `--no-track`，避免错误跟踪 base ref。

## Push 边界

- `git-push` 拒绝直接推送 `main`、`master`、`develop` 或 release 分支，除非用户明确要求。
- 未提交 dirty changes 不会被 push；当推送已有 commit 的意图清楚时可以继续，但必须报告这些未推送改动。
- push 被拒绝后才 fetch 并检查分叉情况。
- rebase、merge 或 `git push --force-with-lease` 前必须询问；默认不使用普通 `git push --force`。

## Supporting Summaries

- [本地 Git helper skills 摘要](../summaries/local-git-helper-skills.md)

## Related Concepts

- [本地 PR review 入口](local-pr-review-entrypoints.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
- [Merge conflict resolution](merge-conflict-resolution.md)
