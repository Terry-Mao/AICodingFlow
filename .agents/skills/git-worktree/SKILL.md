---
name: git-worktree
description: Create isolated local Git worktrees for parallel branch development, using repo branch naming rules and safe defaults.
---

# git-worktree

Use this when the user wants a separate local working directory for another
branch, especially for parallel issue work without disturbing the current
working tree.

This skill mirrors `git-branch` naming and safety rules, but creates a Git
worktree instead of switching the current directory.

## Goal

Create an isolated local worktree at `.worktrees/<branch-slug>` for a new
branch, safely and predictably:

- Issue-backed work uses `<type>/<short-desc>-<issueID>`.
- Custom branch names are normalized like `git-branch`.
- Existing branches or worktrees are reported, not overwritten.
- Current uncommitted changes are not copied into the new worktree.
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
3. Refresh remote refs when possible:
   ```bash
   git fetch
   ```
   If fetch fails, continue only if the user accepts that base freshness was
   not verified.
4. Choose the base ref in this order:
   - `upstream/main`
   - `origin/main`
   - `main`
5. Compare the selected base with its upstream when applicable:
   ```bash
   git rev-list --left-right --count <base>...<upstream>
   ```
   If the base is behind, stop and ask whether to update it before creating the
   worktree.
6. Check for an existing local or remote branch:
   ```bash
   git branch --list <branch-name>
   git branch --remotes --list "*/<branch-name>"
   ```
7. Check for an existing worktree already using the target branch by inspecting
   `git worktree list --porcelain`.
8. Check whether the target directory already exists:
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
   git worktree add -b <branch-name> .worktrees/<branch-slug> <base-ref>
   ```
5. Verify the result:
   ```bash
   git worktree list --porcelain
   git -C .worktrees/<branch-slug> branch --show-current
   git -C .worktrees/<branch-slug> status --short
   ```
6. Report:
   - branch name
   - worktree path
   - base ref
   - whether current dirty changes were excluded
   - next command to enter the worktree

## Guardrails

- Do not run `git worktree remove`, `git worktree prune`, `rm`, `git reset`,
  `git stash`, `git push`, or force commands unless the user explicitly asks.
- Do not create a worktree on protected base branches such as `main`, `master`,
  `develop`, or release branches unless the user explicitly asks.
- Do not copy current uncommitted changes into the new worktree.
- Do not overwrite an existing directory, branch, or worktree.
- If GitHub issue data cannot be fetched, use task context only when it is
  sufficient to name the branch; otherwise ask for the missing title or summary.
