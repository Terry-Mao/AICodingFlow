# 本地 Git helper skills

本地 Git helper skills 用于帮助 agent 在仓库内执行常见 Git 准备动作，同时保持用户当前工作区和远端状态安全。它们是本地开发辅助能力，不会自动提交、推送、删除分支或修改 GitHub issue/PR。

## `git-branch`

`git-branch` skill 用于创建符合仓库命名和 base 分支安全规则的本地工作分支。Issue-backed work 使用 `<type>/<short-desc>-<issueID>` 命名；非 issue 分支使用 `<type>/<user-provided-name>`，不会凭空补 issue ID。分支类型遵循 Conventional Commit 常见类型，例如 `feat`、`fix`、`docs`、`test`、`refactor`、`perf`、`chore`；最终分支名必须通过 `git check-ref-format --branch` 校验。

创建分支前，skill 会用组合本地检查读取当前 worktree、当前分支和目标分支状态；只有远端分支冲突、base freshness 或用户显式要求会影响结果时，才额外检查远端或 fetch。对于同一仓库内的开发，base ref 默认优先使用 `origin/<base>`，只在 fork 工作流或仓库明确要求时使用 `upstream/<base>`。默认 base 是 `main`，必要时使用窄范围 `git fetch origin <base>` 验证远端状态。

从已更新的本地 base 创建分支时，使用 `git switch -c <branch-name> <base>`。如果明确从已 fetch 的远端 base 创建分支，使用 `git switch --no-track -c <branch-name> origin/<base>`，避免新功能分支错误跟踪 base 分支；发布时再由 `git-push` 设置该分支自己的 upstream。

## `git-worktree`

`git-worktree` skill 用于为并行分支工作创建独立的本地 Git worktree。默认目录位于仓库根目录下的 `.worktrees/<branch-name>`，保留分支名中的目录层级，例如 `.worktrees/feat/search-123`；仓库会忽略 `/.worktrees/`，避免 worktree 内容被误纳入 Git、review 或提交流程。

目标分支可以来自 issue 引用或自定义分支名：

- issue-backed work 使用与 `git-branch` 一致的 `<type>/<short-desc>-<issueID>` 命名规则。
- 自定义分支会保留合法 type prefix；没有 type 或上下文时默认使用 `chore`。
- 最终分支名必须通过 `git check-ref-format --branch` 校验。

创建前，skill 会用组合本地检查读取当前 repository 状态、当前分支、已有 worktree、目标分支是否已存在，以及目标 `.worktrees/<branch-name>` 路径是否已存在。远端分支冲突、fetch 和 base freshness 只有影响结果时才检查。若当前 worktree 有未提交改动，创建流程可以继续，但必须明确说明这些改动不会被复制到新 worktree。

`git-worktree` 复用 `git-branch` 的 base 选择策略。对于同一仓库内的开发，默认优先使用 `origin/<base-branch>`，其次使用本地 `<base-branch>`；只在 fork 工作流或仓库明确要求时使用 `upstream/<base-branch>`。默认 base 是 `main`。若本地 base 落后且将从本地 base 创建 worktree，需要先询问是否更新；若 `<base-ref>` 是已 fetch 的 `origin/<base-branch>`，可以直接从远端 base 创建，并说明本地 base 分支未更新。

如果目标 branch、目标 worktree 或目标目录已经存在，`git-worktree` 只报告现有 branch/path 并停止，不覆盖、不删除、不 prune、不强制复用。成功创建时先为带 `/` 的分支名创建父目录，再使用 `git worktree add --no-track -b <branch-name> .worktrees/<branch-name> <base-ref>`，避免新分支自动跟踪 base ref；然后在新 worktree 目录中运行 `pwd`，并报告 branch name、worktree path、base ref、当前 dirty changes 是否被排除、当前 worktree 目录，以及用户在自己 shell 中进入 worktree 的下一步 `cd .worktrees/<branch-name>` 命令。创建成功后，除非用户明确切换到其他目录，同一会话中的后续 agent tool calls 和实现工作默认从 `.worktrees/<branch-name>` 运行；这不会改变用户已经打开的 shell 进程所在目录。

## `git-commit`

`git-commit` skill 用于把当前仓库变更提交为原子、可 review 的 Git commit。提交前会用组合检查读取 `git status --short`、unstaged diff、staged diff 及其 stat；若 staged diff 为空则忽略。只有提交信息约定未知时，才额外读取 `.gitmessage`、`CONTRIBUTING.md`、Git 配置或近期提交。

Commit 边界只按真实关注点拆分，例如行为变更与重构、依赖变动与代码、生成文件与源文件、纯格式化改动或无关 docs/tests。直接相关的测试应与对应修复或功能放在同一提交。Skill 只 stage 目标文件；只有文件级 staging 会混入无关改动时才使用 `git add -p`。

默认提交信息格式为 `type(scope): summary`，type 使用 `feat`、`fix`、`refactor`、`perf`、`docs`、`test`、`build`、`ci` 或 `chore`，scope 在明显时使用。Issue ID 优先来自用户显式说明，其次来自分支名模式；只有用户明确要求关闭或 staged diff 明确完成狭窄 issue 时使用 `Fixes #123`，部分、准备性、docs-only、cleanup-only 或语义不确定的工作使用 `Refs #123`。提交使用普通 `git commit -m`，让 hook 正常运行；hook 失败时停止并报告，不主动使用 `--no-verify`、push、改写历史或 force。

## `git-push`

`git-push` skill 用于在已有 commit 且用户要求 push 或 publish 当前分支时发布本地工作。推送前会用组合检查读取工作树状态、当前分支、upstream 和待推送提交；若 upstream 不存在，则准备 `git push -u origin <branch>`，并只在 commit 集不清楚时额外查看近期本地提交。

Skill 会拒绝直接推送 `main`、`master`、`develop` 或 release 分支，除非用户明确要求。未提交的 dirty changes 不会被 push；当推送已有 commit 的意图仍然清楚时可以继续，但必须报告这些未推送改动。已有 upstream 时使用普通 `git push`，没有 upstream 时使用 `git push -u origin <branch>`。若 push 被拒绝，才 fetch 并检查分叉情况；rebase、merge 或 `git push --force-with-lease` 前必须询问，除非用户明确要求，否则不使用普通 `git push --force`。

来源：PR #94，Issue #92，PR #105，Issue #102，PR #107，Issue #106，PR #109，Issue #108。
