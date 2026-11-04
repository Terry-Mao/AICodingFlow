---
name: git-worktree
description: Create an isolated Git worktree for parallel development with minimal safety checks.
---

# git-worktree

Use this when work should not disturb the current worktree. The new worktree
does not copy uncommitted changes, and it does not change the user's shell
directory.

## Naming

Use the `git-branch` naming rules: issue work is
`<type>/<short-desc>-<issueID>`, other work uses a user-provided name, and no
issue ID is invented. When an issue ID is provided, use one `gh issue view`
call for naming context and continue from the request if it fails. Store the
worktree at `.worktrees/<branch-name>` so branch path segments are preserved.
The repository should ignore `.worktrees/`.

## Base

Base selection has exactly one source of truth: the `## Base` section of the
`git-branch` skill. Do not restate or re-order it here — call `resolve_base`
from that section and use the value it returns. For reference, the order is
documented base → `origin/HEAD` → user choice → `main` fallback, and every
candidate is validated with a ref check before it is used.

Copy both helpers from `git-branch` verbatim (keep them identical when that
section changes):

```bash
ref_exists() {
  git rev-parse --verify --quiet "origin/$1" >/dev/null 2>&1 \
    || git rev-parse --verify --quiet "refs/heads/$1" >/dev/null 2>&1
}

resolve_base() {
  local documented="$1" user_base="$2" origin_head cand
  # 1) documented base
  if [ -n "$documented" ] && ref_exists "$documented"; then echo "$documented"; return 0; fi
  # 2) origin/HEAD
  origin_head=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
  [ -n "$origin_head" ] || origin_head=$(git remote show origin 2>/dev/null | sed -n 's/^ *HEAD branch: *//p')
  # 3) user choice  4) main fallback
  for cand in "$origin_head" "$user_base" main; do
    if [ -n "$cand" ] && ref_exists "$cand"; then echo "$cand"; return 0; fi
  done
  return 1
}
```

Create from the remote ref first and fall back to the local ref only when the
remote one is missing:

```bash
base=$(resolve_base "$documented_base" "$user_base") || {
  echo "No usable base branch. Candidates:" >&2
  git branch -r >&2
  echo "Pass --base <branch> to choose one." >&2
  exit 1
}
if git rev-parse --verify --quiet "origin/$base" >/dev/null; then
  base_ref="origin/$base"
else
  base_ref="$base"
fi
```

Same-repository work prefers `origin/<base>`; use `upstream` only for fork
workflows or explicit guidance. Fetch or compare freshness only when it can
change the choice of base. If the local base is stale, confirm before using it
or create from a fetched remote base and report that the local base was
unchanged. Never continue with a base that does not resolve, and never fall back
to a `main` branch that does not exist.

## Create

Before creating, check current status, existing worktrees/branches, and the
target path. Stop if any target already exists or dirty-work intent is unclear.
Validate the branch with `git check-ref-format --branch <branch-name>`, create
parent directories as needed, resolve the base as shown above, then run the
equivalent of:

```bash
git worktree add --no-track -b <branch-name> .worktrees/<branch-name> "$base_ref"
```

Verify the new worktree's branch, status, and `pwd`. Report its path, base,
whether dirty changes were excluded, and the user's next step:
`cd .worktrees/<branch-name>`.

Do not remove, prune, overwrite, reset, stash, push, or force anything unless
explicitly asked. Do not create protected/shared base branches as targets.
Subsequent agent work uses the new worktree unless the user says otherwise.
