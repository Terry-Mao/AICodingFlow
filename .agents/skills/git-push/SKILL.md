---
name: git-push
description: Push committed branch work to the correct remote branch, setting upstream when needed and avoiding unsafe force pushes.
---

# git-push

Use after commits exist and the user asks to push or publish the branch.

## Workflow

1. Inspect only what affects the push:
   ```bash
   git status --short
   git branch --show-current
   git rev-parse --abbrev-ref --symbolic-full-name @{u}
   ```
   If there is no upstream, that command may fail; continue by preparing `git push -u origin <branch>`.

2. Refuse protected/shared base branches (`main`, `master`, `develop`, release branches) unless the user explicitly asked to push them.

3. If the worktree is dirty, report that those changes are not included in the push. Continue when pushing existing commits is still clearly what the user requested; ask only if the dirty state makes intent ambiguous.

4. Show what will be pushed when an upstream exists:
   ```bash
   git log --oneline @{u}..HEAD
   ```
   If there is no upstream, use recent local commits only when the commit set is unclear.

5. Push normally so Git hooks run:
   ```bash
   git push
   ```
   or, without upstream:
   ```bash
   git push -u origin <branch>
   ```

## Rejections

If push is rejected, do not force-push by default. Fetch and inspect divergence only after rejection, then ask before rebasing, merging, or using `git push --force-with-lease`.

Never use plain `git push --force` unless the user explicitly requests that exact behavior.

## Reporting

After pushing, report the current branch, remote branch/upstream, pushed commit hash, push result, and any dirty changes that were not pushed.
