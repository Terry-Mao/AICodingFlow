---
name: git-worktree
description: Create isolated local Git worktrees for parallel branch development, using repo branch naming rules and safe defaults.
---

# git-worktree

Use this when the user wants a separate local working directory for another
branch, especially for parallel issue work without disturbing the current
working tree.

This skill mirrors `git-branch` naming and safety rules, but creates a Git
worktree and then defaults subsequent work in the conversation to the new
worktree directory.

## Goal

Create an isolated local worktree at `.worktrees/<branch-slug>` for a new
branch, safely and predictably:

- Issue-backed work uses `<type>/<short-desc>-<issueID>`.
- Custom branch names are normalized like `git-branch`.
- Existing branches or worktrees are reported, not overwritten.
- Current uncommitted changes are not copied into the new worktree.
- After successful creation, subsequent commands should run from the new
  worktree directory by default.
- No commit, push, delete, prune, stash, or force operation is performed.

## Directory Rules

- Default parent directory: `.worktrees/` at the repository root.
- Convert the final branch name into the directory slug by replacing `/` with
  `-`.
- Example:
  - branch: `feat/git-worktree-skill-92`
  - directory: `.worktrees/feat-git-worktree-skill-92`
- `.worktrees/` must stay ignored by Git.

## Branch Name Resolution

Follow the same naming rules as `.agents/skills/git-branch/SKILL.md`.

For an issue reference such as `#92`:

1. Fetch issue data:
   ```bash
   gh issue view <issueID> --json title,body,number
   ```
2. Derive the branch type and short description from the issue title.
3. Build `<type>/<short-desc>-<issueID>`.

For a custom branch name:

1. Preserve a valid type prefix such as `fix/login-error`.
2. Use an explicitly requested type when provided.
3. Infer the type from task context when available.
4. Use `chore` when no type or task context is available.

Normalize branch names by lowercasing, replacing spaces and repeated
separators with `-`, removing punctuation and non-branch characters, trimming
leading/trailing separators, and keeping the result short and specific.

Validate the final branch:

```bash
git check-ref-format --branch <branch-name>
```

## Safety Checks

Run these checks before creating a worktree:

1. Inspect the current repository state:
   ```bash
   git status --short
   git branch --show-current
   git worktree list --porcelain
   git remote -v
   ```
2. If the current worktree is dirty, continue only after clearly reporting that
   these uncommitted changes will not be copied into the new worktree.
3. Resolve the expected base branch using the same policy as `git-branch`:
   prefer the repository's documented development base, usually `main`,
   `master`, `develop`, or a release branch named by repo guidance. In this
   repository, default to `main` unless repo guidance or the user names a
   different base.
4. For same-repository development, prefer `origin/<base-branch>` over
   `upstream/<base-branch>`. Use `upstream` only for fork workflows or explicit
   repo guidance.
5. Refresh the selected base refs when possible. For the default case,
   run:
   ```bash
   git fetch origin main
   ```
   If fetch fails, continue only if the user accepts that base freshness was
   not verified.
6. Choose the base ref in this order:
   - `origin/<base-branch>` when it exists
   - local `<base-branch>` when it exists
   - `upstream/<base-branch>` only for fork workflows or explicit repo guidance
7. Compare the local base with `origin/<base-branch>` when both exist:
   ```bash
   git rev-list --left-right --count <base-branch>...origin/<base-branch>
   ```
   If the local base is behind, stop and ask whether to update it before
   creating the worktree. If creating directly from `origin/<base-branch>`,
   report that the local base branch was not updated.
8. Check for an existing local or remote branch:
   ```bash
   git branch --list <branch-name>
   git branch --remotes --list "*/<branch-name>"
   ```
9. Check for an existing worktree already using the target branch by inspecting
   `git worktree list --porcelain`.
10. Check whether the target directory already exists:
   ```bash
   test -e .worktrees/<branch-slug>
   ```

If the branch, worktree, or target directory already exists, do not overwrite,
delete, prune, or reuse it automatically. Report the existing branch/path and
stop.

## Workflow

1. Resolve and validate the target branch name.
2. Resolve the worktree directory as `.worktrees/<branch-slug>`.
3. Run all safety checks above.
4. Create the worktree and branch:
   ```bash
   git worktree add --no-track -b <branch-name> .worktrees/<branch-slug> <base-ref>
   ```
   For same-repository development, `<base-ref>` should normally be
   `origin/main` after `git fetch origin main`. Keep `--no-track` so the new
   branch does not track the base; `git-push` sets its upstream when published.
5. Verify the result:
   ```bash
   git worktree list --porcelain
   git -C .worktrees/<branch-slug> branch --show-current
   git -C .worktrees/<branch-slug> status --short
   pwd
   ```
   Run `pwd` with the command working directory set to
   `.worktrees/<branch-slug>` so the user can confirm the active directory.
6. Treat `.worktrees/<branch-slug>` as the default working directory for
   subsequent tool calls and implementation work in this conversation unless
   the user explicitly switches elsewhere.
7. Report:
   - branch name
   - worktree path
   - base ref
   - whether current dirty changes were excluded
   - current working directory inside the new worktree
   - next command to enter the worktree in the user's own shell

## Guardrails

- Do not run `git worktree remove`, `git worktree prune`, `rm`, `git reset`,
  `git stash`, `git push`, or force commands unless the user explicitly asks.
- Do not create a worktree on protected base branches such as `main`, `master`,
  `develop`, or release branches unless the user explicitly asks.
- Do not copy current uncommitted changes into the new worktree.
- Do not overwrite an existing directory, branch, or worktree.
- If GitHub issue data cannot be fetched, use task context only when it is
  sufficient to name the branch; otherwise ask for the missing title or summary.
