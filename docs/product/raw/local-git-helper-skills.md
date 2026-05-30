# 本地 Git helper skills

本地 Git helper skills 用于帮助 agent 在仓库内执行常见 Git 准备动作，同时保持用户当前工作区和远端状态安全。它们是本地开发辅助能力，不会自动提交、推送、删除分支或修改 GitHub issue/PR。

## `git-worktree`

`git-worktree` skill 用于为并行分支工作创建独立的本地 Git worktree。默认目录位于仓库根目录下的 `.worktrees/<branch-slug>`，其中 `<branch-slug>` 由最终分支名把 `/` 替换为 `-` 得到；仓库会忽略 `/.worktrees/`，避免 worktree 内容被误纳入 Git、review 或提交流程。

目标分支可以来自 issue 引用或自定义分支名：

- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 自定义分支会保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。

创建前，skill 会检查当前 repository 状态、当前分支、已有 worktree、remote/base 状态、目标分支是否已存在，以及目标 `.worktrees/<branch-slug>` 路径是否已存在。若当前 worktree 有未提交改动，创建流程可以继续，但必须明确说明这些改动不会被复制到新 worktree。

默认 base ref 按 `upstream/main`、`origin/main`、`main` 的顺序选择。若仓库有 remote 且网络可用，Git helper 在检查 base 是否最新前运行 `git fetch`；如果无法 fetch，必须说明 base freshness 未验证。

如果目标 branch、目标 worktree 或目标目录已经存在，`git-worktree` 只报告现有 branch/path 并停止，不覆盖、不删除、不 prune、不强制复用。成功创建时使用 `git worktree add -b <branch-name> .worktrees/<branch-slug> <base-ref>`，然后报告 branch name、worktree path、base ref、当前 dirty changes 是否被排除，以及进入 worktree 的下一步命令。

来源：PR #94，Issue #92。
