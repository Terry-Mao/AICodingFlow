---
name: git-worktree
description: Create an isolated Git worktree for parallel development with minimal safety checks.
---

# git-worktree

Use this when work should not disturb the current worktree. The new worktree
does not copy uncommitted changes, and it does not change the user's shell
directory.

## Naming and base

Use the `git-branch` naming rules: issue work is
`<type>/<short-desc>-<issueID>`, other work uses a user-provided name, and no
issue ID is invented. When an issue ID is provided, use one `gh issue view`
call for naming context and continue from the request if it fails. Store the
worktree at `.worktrees/<branch-name>` so branch path segments are preserved.
The repository should ignore `.worktrees/`.

Default the base to `main`; same-repository work prefers `origin/<base>`, then
local `<base>`, and uses `upstream` only for fork workflows or explicit
guidance. Fetch/check freshness only when it affects the result. If the local
base is stale, confirm before using it or create from a fetched remote base and
report that the local base was unchanged.

## Create

Before creating, check current status, existing worktrees/branches, and the
target path. Stop if any target already exists or dirty-work intent is unclear.
Validate the branch with `git check-ref-format --branch <branch-name>`, create
parent directories as needed, then run the equivalent of:

```bash
git worktree add --no-track -b <branch-name> .worktrees/<branch-name> <base-ref>
```

Verify the new worktree's branch, status, and `pwd`. Report its path, base,
whether dirty changes were excluded, and the user's next step:
`cd .worktrees/<branch-name>`.

Do not remove, prune, overwrite, reset, stash, push, or force anything unless
explicitly asked. Do not create protected/shared base branches as targets.
Subsequent agent work uses the new worktree unless the user says otherwise.
