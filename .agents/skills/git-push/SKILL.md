---
name: git-push
description: Publish committed work to the correct remote branch without unsafe force pushes.
---

# git-push

Use this after commits exist and the user asks to push or publish the current
branch.

Check worktree status, current branch, upstream, and commits not yet on the
upstream. Refuse `main`, `master`, `develop`, and release branches unless the
user explicitly asks. Dirty changes are not pushed; report them and continue
only when pushing existing commits is clearly intended.

Use ordinary push for an existing upstream, otherwise set the branch upstream:

```bash
git push
git push -u origin <branch>
```

If rejected, fetch and inspect divergence. Ask before rebasing, merging, or
using `--force-with-lease`; never use plain `--force` unless explicitly
requested. Report branch, remote/upstream, pushed commit, result, and any dirty
changes left behind.
