---
name: git-worktree
description: Create isolated local Git worktrees for parallel branch development using efficient branch naming and safety checks.
---

# git-worktree

Use when the user wants a separate local working directory for another branch without disturbing the current worktree.

## Goal

Create `.worktrees/<branch-slug>` for a new branch, then treat that worktree as the default directory for subsequent Codex tool calls. This does not change the user's existing shell process; report the `cd` command the user should run locally.

- Issue-backed branch: `<type>/<short-desc>-<issueID>`.
- Custom branch: normalize like `git-branch`.
- Directory slug: replace `/` in the branch name with `-`.
- Do not copy uncommitted changes into the new worktree.
- Do not overwrite existing branches, worktrees, or directories.

## Branch Name

Follow `git-branch` naming rules. Fetch issue metadata only when an issue ID is given:

```bash
gh issue view <issueID> --json title,body,number
```

If GitHub is unavailable but the request has enough context, continue and state that issue metadata was not verified; otherwise ask for the missing title or summary.

Validate:

```bash
git check-ref-format --branch <branch-name>
```

## Efficient Safety Checks

Run:

```bash
git status --short
git branch --show-current
git worktree list --porcelain
git branch --list <branch-name>
test -e .worktrees/<branch-slug>
```

Check remotes or fetch only when freshness matters, a remote branch conflict is plausible, or the user asked for up-to-date base state:

```bash
git branch --remotes --list '*/<branch-name>'
git fetch origin <base>
```

For same-repository work, prefer `origin/<base>` over `upstream/<base>`. Use `upstream` only for fork workflows or explicit repo guidance. Default `<base>` to `main` unless repo guidance or the user names another base. Choose the base from the first suitable available ref:

1. `origin/<base>`
2. local `<base>`
3. `upstream/<base>` only for fork workflows or explicit repo guidance

Compare freshness only when using a local base that may be behind and that matters for this work:

```bash
git rev-list --left-right --count <base>...origin/<base>
```

If local `<base>` is behind and you are using local `<base>`, ask whether to update it or branch directly from `origin/<base>`. If using `origin/<base>`, proceed and report that local `<base>` was not updated.

Stop and ask only if the branch/worktree/directory exists, base choice is unsafe or stale for the requested work, or dirty current changes make intent ambiguous. Otherwise report that dirty current changes, if any, will not be copied.

## Create And Verify

Create:

```bash
git worktree add --no-track -b <branch-name> .worktrees/<branch-slug> <base-ref>
```

For same-repository development, `<base-ref>` should normally be `origin/main` when it is available. Keep `--no-track` so the new branch does not track the base; `git-push` sets its upstream when published.

Verify:

```bash
git worktree list --porcelain
git -C .worktrees/<branch-slug> branch --show-current
git -C .worktrees/<branch-slug> status --short
pwd
```

Run `pwd` from inside the new worktree.

## Reporting

Report the branch name, worktree path, base ref, whether dirty current changes were excluded, current directory inside the new worktree, and the `cd` command for the user's shell.

## Guardrails

- Do not run `git worktree remove`, `git worktree prune`, `rm`, `git reset`, `git stash`, `git push`, or force commands unless explicitly asked.
- Do not create worktrees on protected base branches as the target branch (`main`, `master`, `develop`, release branches) unless explicitly asked.
- Do not overwrite or reuse existing branch/worktree/directory automatically.
- Keep `.worktrees/` ignored by Git.
