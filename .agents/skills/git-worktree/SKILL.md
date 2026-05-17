---
name: git-worktree
description: Create isolated Git worktrees for parallel branch work with efficient naming, base selection, and safety checks.
---

# git-worktree

Create a separate worktree without disturbing the current one, then use the new directory for subsequent Codex tool calls. This does not change the user's existing shell; report the `cd` command.

## Naming And Path

- Branch names follow `git-branch`.
- Issue-backed: `<type>/<short-desc>-<issueID>`.
- Worktree path preserves the branch path: `.worktrees/<branch-name>`, for example `.worktrees/feat/search-123`.
- Do not copy current uncommitted changes.
- Do not overwrite existing branches, worktrees, or directories.

Fetch issue metadata only when an issue ID is given:

```bash
gh issue view <issueID> --json title,body,number
```

Validate:

```bash
git check-ref-format --branch <branch-name>
```

## Efficient Checks

Use one tool call for local state:

```bash
git status --short
git branch --show-current
git worktree list --porcelain
git branch --list <branch-name>
test -e .worktrees/<branch-name>
```

Add remote/freshness checks only when they matter:

```bash
git branch --remotes --list '*/<branch-name>'
git fetch origin <base>
git rev-list --left-right --count <base>...origin/<base>
```

Base policy:

- Default `<base>` to `main` unless repo guidance or the user names another base.
- Same-repo work prefers `origin/<base>`, then local `<base>`.
- Use `upstream/<base>` only for fork workflows or explicit guidance.
- If local `<base>` is stale but `origin/<base>` is selected, proceed and report that local `<base>` was not updated.

Stop only if branch/worktree/path exists, base selection is unsafe or stale for the work, or dirty current changes make intent ambiguous. Otherwise report that dirty current changes, if any, are excluded.

## Create And Verify

Create the parent directory when the branch name contains `/`, then add the worktree:

```bash
mkdir -p .worktrees/<type>
git worktree add --no-track -b <branch-name> .worktrees/<branch-name> <base-ref>
```

For same-repo work, `<base-ref>` is normally `origin/main` when available. Keep `--no-track`; `git-push` sets the branch upstream when published.

Verify in one call:

```bash
git worktree list --porcelain
git -C .worktrees/<branch-name> branch --show-current
git -C .worktrees/<branch-name> status --short
pwd
```

Run `pwd` from inside the new worktree.

Report branch, path, base ref, whether dirty changes were excluded, current directory, and the user's `cd .worktrees/<branch-name>` command.

## Guardrails

- No `git worktree remove`, `git worktree prune`, `rm`, `git reset`, `git stash`, `git push`, or force commands unless explicitly asked.
- Do not create protected/shared base branches as target branches unless explicitly asked.
- Keep `.worktrees/` ignored by Git.
