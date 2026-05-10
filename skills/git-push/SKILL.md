---
name: git-push
description: Push committed branch work to the correct GitHub remote branch, set upstream when needed, and avoid unsafe force pushes.
---

# git-push

Use this after `git-commit` when the user asks to push committed work or publish a branch.

## Goal

Publish the current development branch safely without rewriting remote history or pushing unfinished work by accident.

## Workflow

1. **Inspect**
   Run:
   ```bash
   git status --short
   git branch --show-current
   git remote -v
   ```
   If the worktree is dirty, do not include those changes in the push; report them and continue only if the user explicitly wants to push existing commits anyway.

2. **Protect base branches**
   Do not push directly to protected or shared base branches such as `main`, `master`, `develop`, or release branches unless the user explicitly requests it.

3. **Check upstream and commits**
   Determine whether the current branch has an upstream.
   If it does, check what will be pushed with:
   ```bash
   git log --oneline @{u}..HEAD
   ```
   If it does not, check recent local commits and prepare to set upstream.

4. **Push**
   Use normal `git push` so any configured `pre-push` hook runs. If the hook fails, stop and report the failure instead of bypassing it.
   If no upstream exists, use:
   ```bash
   git push -u origin <branch>
   ```
   If upstream exists, use:
   ```bash
   git push
   ```

5. **Handle rejection safely**
   If push is rejected, do not force push by default.
   Fetch first, inspect divergence, and ask before rebasing, merging, or using `git push --force-with-lease`.
   Never use plain `git push --force` unless the user explicitly requests that exact behavior.

## Reporting

After pushing, report:

- current branch
- remote branch
- pushed commit hash
- push result
- any dirty worktree changes that were not pushed
