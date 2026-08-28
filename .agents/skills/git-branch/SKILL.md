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

## Create

Check the current worktree, branch, and target branch first. Stop if the
worktree intent is ambiguous, the target already exists, or the current/base
branch is unsafe. Validate the name with:

```bash
git check-ref-format --branch <branch-name>
```

Use the repository's documented base, otherwise `main`. In the same repository
prefer `origin/<base>` over `upstream/<base>`; use `upstream` only for a fork or
explicit guidance. Fetch or compare freshness only when it can change the
choice of base. If creating from a stale local base, confirm before updating or
use a freshly fetched remote base and report that the local base was unchanged.

```bash
git switch -c <branch-name> <base>
git switch --no-track -c <branch-name> origin/<base>
```

Verify the resulting branch. Do not switch to an existing branch, overwrite,
reset, stash, delete, or force anything without explicit user intent. Do not
create protected/shared base branches.
