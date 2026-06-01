---
type: summary
title: 本地 Git helper skills 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/local-git-helper-skills.md
---

# 本地 Git helper skills 摘要

Source: [docs/product/raw/local-git-helper-skills.md](../../raw/local-git-helper-skills.md)

本地 Git helper skills 帮助 agent 在仓库内执行常见 Git 准备动作，同时保持用户当前工作区和远端状态安全。它们是本地开发辅助能力，不会自动提交、推送、删除分支或修改 GitHub issue/PR。

## `git-branch`

- `git-branch` 用于创建符合仓库命名和 base 分支安全规则的本地工作分支。
- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 非 issue 分支使用 `<type>/<user-provided-name>`，不会凭空补 issue ID。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。
- 对于同一仓库内开发，base ref 默认优先使用 `origin/<base>`；只在 fork 工作流或仓库明确要求时使用 `upstream/<base>`。
- 默认 base 是 `main`，必要时使用窄范围 `git fetch origin <base>` 验证远端状态。
- 从远端 base 创建分支时使用 `git switch --no-track -c <branch-name> origin/<base>`，避免新功能分支错误跟踪 base。

## `git-worktree`

- `git-worktree` 用于为并行分支工作创建独立的本地 Git worktree。
- 默认目录位于仓库根目录下的 `.worktrees/<branch-name>`，保留分支名中的目录层级，例如 `.worktrees/feat/search-123`。
- 仓库忽略 `/.worktrees/`，避免 worktree 内容被误纳入 Git、review 或提交流程。
- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 自定义分支保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。

## 创建前检查

- skill 会检查当前 repository 状态、当前分支、已有 worktree、目标分支是否已存在，以及目标 `.worktrees/<branch-name>` 路径是否已存在。
- 远端分支冲突、fetch 和 base freshness 只有影响结果时才检查。
- 当前 worktree 有未提交改动时，创建流程可以继续，但必须明确说明这些改动不会被复制到新 worktree。
- `git-worktree` 复用 `git-branch` 的 base 选择策略：同一仓库内默认优先使用 `origin/<base-branch>`，其次使用本地 `<base-branch>`；只在 fork 工作流或仓库明确要求时使用 `upstream/<base-branch>`。
- 若本地 base 落后且将从本地 base 创建 worktree，需要先询问是否更新。

## 安全边界

- 如果目标 branch、目标 worktree 或目标目录已经存在，`git-worktree` 只报告现有 branch/path 并停止。
- skill 不覆盖、不删除、不 prune、不强制复用已存在的 branch、worktree 或目录。
- 成功创建时先为带 `/` 的分支名创建父目录，再使用 `git worktree add --no-track -b <branch-name> .worktrees/<branch-name> <base-ref>`。
- 成功后报告 branch name、worktree path、base ref、当前 dirty changes 是否被排除、当前 worktree 目录，以及进入 worktree 的下一步命令。
- 创建成功后，除非用户明确切换到其他目录，同一会话后续 agent tool calls 和实现工作默认从新 worktree 运行。

## `git-commit` 与 `git-push`

- `git-commit` 将当前变更提交为原子、可 review 的 commit；只 stage 目标文件，hook 失败时停止并报告。
- 默认提交信息为 `type(scope): summary`，Issue footer 只在语义明确时使用 `Fixes #123`，否则使用 `Refs #123`。
- `git-push` 在已有 commit 且用户要求 push 或 publish 时发布当前分支。
- `git-push` 拒绝直接推送 `main`、`master`、`develop` 或 release 分支，除非用户明确要求。
- push 被拒绝后才 fetch 并检查分叉；rebase、merge 或 `git push --force-with-lease` 前必须询问，默认不使用普通 force push。

## 支持的概念

- [本地 Git helper skills](../concepts/local-git-helper-skills.md)
- [Merge conflict resolution](../concepts/merge-conflict-resolution.md)
