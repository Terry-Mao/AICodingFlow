---
name: git-branch
description: Create repository-compliant branches with efficient issue naming, base selection, and safety checks.
---

# git-branch

Create a development branch with the fewest checks needed to avoid wrong names, wrong bases, or overwrites.

## Naming

- Issue-backed: `<type>/<short-desc>-<issueID>`.
- Non-issue: `<type>/<user-provided-name>`; never invent an issue ID.
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`.
- Preserve a valid user type; otherwise infer from the task, defaulting to `chore`.
- Normalize to short lowercase English words separated by `-`; remove punctuation, filler words, repeated separators, and non-branch characters.

If the user gives an issue reference, run one `gh` call:

```bash
gh issue view <issueID> --json title,body,number
```

Use the title for `short-desc`; fall back to body or user context only when needed. If no issue is mentioned, do not call `gh`. If `gh` fails but context is enough, continue and report that issue metadata was not verified.

Validate:

```bash
git check-ref-format --branch <branch-name>
```

## Efficient Checks

Prefer one shell call for local checks:

```bash
git status --short
git branch --show-current
git branch --list <branch-name>
```

Add remote/freshness checks only when they affect the result:

```bash
git branch --remotes --list '*/<branch-name>'
git fetch origin <base>
git rev-list --left-right --count <base>...origin/<base>
```

Base policy:

- Default `<base>` to `main` unless repo guidance or the user names another base.
- Same-repo work prefers `origin/<base>` over `upstream/<base>`.
- Use `upstream` only for fork workflows or explicit guidance.
- Do not make the new branch track the base; `git-push` sets upstream later.

Stop only when the target branch exists, dirty worktree intent is ambiguous, the current/base branch is clearly unsafe, or freshness checks show the selected base is stale.

## Create

Use one of:

```bash
git switch -c <branch-name> <base>
git switch --no-track -c <branch-name> origin/<base>
```

Then verify with:

```bash
git branch --show-current
```

## Guardrails

- No overwrite, reset, stash, delete, or force operations unless explicitly asked.
- Do not switch to an existing branch without user intent.
- Do not create protected/shared base branches (`main`, `master`, `develop`, release branches) unless explicitly asked.
- Report skipped freshness checks only when they could matter.
