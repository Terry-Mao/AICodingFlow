# 本地 Git helper skills

本地 Git helper skills 用于帮助 agent 在仓库内执行常见 Git 准备动作，同时保持用户当前工作区和远端状态安全。它们是本地开发辅助能力，不会自动提交、推送、删除分支或修改 GitHub issue/PR。

## `git-branch`

`git-branch` skill 用于创建符合仓库命名和 base 分支安全规则的本地工作分支。Issue-backed work 使用 `<type>/<short-desc>-<issueID>` 命名；非 issue 分支使用 `<type>/<user-provided-name>`，不会凭空补 issue ID。分支类型遵循 Conventional Commit 常见类型，例如 `feat`、`fix`、`docs`、`test`、`refactor`、`perf`、`chore`；最终分支名必须通过 `git check-ref-format --branch` 校验。

创建分支前，skill 会检查当前 worktree 是否有未提交改动、目标分支是否已存在、当前 base 是否合适，以及 base freshness 是否已验证。对于同一仓库内的开发，base ref 默认优先使用 `origin/<base>`，只在 fork 工作流或仓库明确要求时使用 `upstream/<base>`。默认 `main` base 的远端刷新命令是 `git fetch origin main`；如果无法 fetch，必须说明 base freshness 未验证。

从已更新的本地 base 创建分支时，使用 `git switch -c <branch-name> <base>`。如果明确从已 fetch 的远端 base 创建分支，使用 `git switch --no-track -c <branch-name> origin/<base>`，避免新功能分支错误跟踪 base 分支；发布时再由 `git-push` 设置该分支自己的 upstream。

## `git-worktree`

`git-worktree` skill 用于为并行分支工作创建独立的本地 Git worktree。默认目录位于仓库根目录下的 `.worktrees/<branch-slug>`，其中 `<branch-slug>` 由最终分支名把 `/` 替换为 `-` 得到；仓库会忽略 `/.worktrees/`，避免 worktree 内容被误纳入 Git、review 或提交流程。

目标分支可以来自 issue 引用或自定义分支名：

- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 自定义分支会保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。

创建前，skill 会检查当前 repository 状态、当前分支、已有 worktree、remote/base 状态、目标分支是否已存在，以及目标 `.worktrees/<branch-slug>` 路径是否已存在。若当前 worktree 有未提交改动，创建流程可以继续，但必须明确说明这些改动不会被复制到新 worktree。

`git-worktree` 复用 `git-branch` 的 base 选择策略。对于同一仓库内的开发，默认优先使用 `origin/<base-branch>`，其次使用本地 `<base-branch>`；只在 fork 工作流或仓库明确要求时使用 `upstream/<base-branch>`。默认 `main` base 的远端刷新命令是 `git fetch origin main`；如果无法 fetch，必须说明 base freshness 未验证。若本地 base 落后且将从本地 base 创建 worktree，需要先询问是否更新；若 `<base-ref>` 是已 fetch 的 `origin/<base-branch>`，可以直接从远端 base 创建，并说明本地 base 分支未更新。

如果目标 branch、目标 worktree 或目标目录已经存在，`git-worktree` 只报告现有 branch/path 并停止，不覆盖、不删除、不 prune、不强制复用。成功创建时使用 `git worktree add --no-track -b <branch-name> .worktrees/<branch-slug> <base-ref>`，避免新分支自动跟踪 base ref；然后在新 worktree 目录中运行 `pwd`，并报告 branch name、worktree path、base ref、当前 dirty changes 是否被排除、当前 worktree 目录，以及用户在自己 shell 中进入 worktree 的下一步 `cd .worktrees/<branch-slug>` 命令。创建成功后，除非用户明确切换到其他目录，同一会话中的后续 agent tool calls 和实现工作默认从 `.worktrees/<branch-slug>` 运行；这不会改变用户已经打开的 shell 进程所在目录。

来源：PR #94，Issue #92，PR #105，Issue #102，PR #107，Issue #106。
