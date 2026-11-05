---
name: git-branch
description: Create repository-compliant development branches with minimal safety checks.
---

# git-branch

Create a new branch without overwriting work or choosing an unsafe base.

## Naming

- Issue-backed work: `<type>/<short-desc>-<issueID>`.
- Other work: `<type>/<user-provided-name>`; never invent an issue ID.
- Valid types are `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, and
  `chore`. Preserve a valid user type, otherwise infer one and default to
  `chore`.
- Keep the description short, lowercase, English, hyphen-separated, and valid
  for Git. Remove punctuation, filler, and repeated separators.

When an issue ID is provided, use one `gh issue view <issueID> --json
title,body,number` call for naming context. If it fails, continue only when the
request is enough and report that the issue was not verified.

## Base

This section is the single source of truth for base selection. Other skills
(`git-worktree`) reference it and copy the snippet below instead of restating a
second rule set.

Resolve the base in exactly this order, validating every candidate with a ref
check and falling through to the next one when it does not resolve:

1. the repository's documented base — the default branch the repository itself
   states (for example in `CONTRIBUTING`, `README`, or `AGENTS`); skip this step
   when nothing is documented;
2. `origin/HEAD` — the remote's default branch;
3. the branch the user explicitly asked for (`--base <branch>` or a branch named
   in the request);
4. `main` as the last resort.

Never continue with a base that does not resolve. If no candidate resolves, list
the available remote branches, ask the user to pass `--base <branch>`, and exit
non-zero — do not silently fall back to a `main` that does not exist.

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

The order is deliberate: `origin/HEAD` is checked before the user choice, so an
explicit `--base` does not override a resolvable `origin/HEAD`. Surface that
conflict to the user instead of silently reordering the rule.

## Create

Check the current worktree, branch, and target branch first. Stop if the
worktree intent is ambiguous, the target already exists, or the current/base
branch is unsafe. Validate the name with:

```bash
git check-ref-format --branch <branch-name>
```

Resolve the base with the snippet from the Base section, then prefer the remote
ref and use the local ref only when the remote one is missing:

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

git switch --no-track -c <branch-name> "$base_ref"
```

In the same repository prefer `origin/<base>` over `upstream/<base>`; use
`upstream` only for a fork or explicit guidance. Fetch or compare freshness only
when it can change the choice of base. If creating from a stale local base,
confirm before updating or use a freshly fetched remote base and report that the
local base was unchanged.

Verify the resulting branch. Do not switch to an existing branch, overwrite,
reset, stash, delete, or force anything without explicit user intent. Do not
create protected/shared base branches.
