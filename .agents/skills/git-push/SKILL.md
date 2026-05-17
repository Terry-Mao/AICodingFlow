---
name: git-push
description: Push committed branch work to the correct remote branch with minimal checks and no unsafe force pushes.
---

# git-push

Use after commits exist and the user asks to push or publish the branch.

## Inspect

Use one tool call for push state:

```bash
git status --short
git branch --show-current
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git log --oneline @{u}..HEAD
```

If upstream lookup fails, prepare `git push -u origin <branch>` and use recent local commits only when the commit set is unclear.

## Push

- Refuse protected/shared base branches (`main`, `master`, `develop`, release branches) unless explicitly asked.
- Dirty worktree changes are not pushed; report them and continue only when pushing existing commits is still clearly intended.
- Use normal push so hooks run:

```bash
git push
git push -u origin <branch>
```

## Rejections

If push is rejected, then fetch and inspect divergence. Ask before rebasing, merging, or using `git push --force-with-lease`. Never use plain `git push --force` unless the user explicitly requests that exact behavior.

Report current branch, upstream/remote branch, pushed commit hash, push result, and dirty changes that were not pushed.
