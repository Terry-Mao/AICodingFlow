---
name: git-branch
description: Create repository-compliant branches, especially issue-backed branches using type/short-desc-issueID.
---

# git-branch

Use when creating a new development branch. Optimize for a correct branch name and safe creation with the fewest checks needed for the current repo state.

## Branch Naming

- Issue-backed branch: `<type>/<short-desc>-<issueID>`.
- Non-issue branch: `<type>/<user-provided-name>`.
- Valid types: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`.
- Prefer short lowercase hyphenated English names under 80 characters.
- Do not invent an issue number.
- Preserve an explicit valid type from the user; otherwise infer from the work, falling back to `chore`.

Normalize names by lowercasing, replacing spaces/underscores/repeated separators with `-`, removing punctuation and non-branch characters, dropping filler words, trimming separators, and keeping the smallest meaningful phrase.

Validate:

```bash
git check-ref-format --branch <branch-name>
```

## Issue Handling

If the user gives an issue reference (`#123`, issue URL, or clear task ID), fetch only what is needed:

```bash
gh issue view <issueID> --json title,body,number
```

Derive `short-desc` from the title, using the body or user context only if the title normalizes poorly. If GitHub is unavailable but the request already contains enough context to name the branch, continue and state that issue metadata was not verified; otherwise ask for the missing title or summary.

If no issue is mentioned, do not call `gh`.

## Efficient Safety Checks

Before creating the branch, run:

```bash
git status --short
git branch --show-current
git branch --list <branch-name>
```

Check remotes only when a remote branch conflict is plausible or a fresh remote view matters:

```bash
git branch --remotes --list '*/<branch-name>'
```

For same-repository work, prefer `origin/<base>` over `upstream/<base>`. Use `upstream` only for fork workflows or explicit repo guidance. Default `<base>` to `main` unless repo guidance or the user names another base. Do not make the new branch track the base branch; `git-push` sets the upstream when published.

Use existing local information when it is enough. Do not run `git fetch` by default; run it only when the user asks for fresh remote state, the base may be stale, or remote branch existence matters. When freshness matters, prefer a narrow fetch:

```bash
git fetch origin <base>
```

If local `<base>` is behind and you are using local `<base>`, ask whether to update it or branch directly from `origin/<base>`. If using `origin/<base>`, proceed and report that local `<base>` was not updated.

Stop and ask only when:

- the target branch already exists and it is not already active;
- the worktree is dirty and creating from the current state is ambiguous;
- the current branch is clearly an unsafe base, such as a release branch or unrelated feature branch;
- base freshness matters and fetch/status shows the selected base is stale.

## Create

1. Resolve issue ID and branch name from the user request. Read repo guidance only if branch conventions are unknown or visible guidance already exists in context.
2. Validate the branch name.
3. Run the efficient safety checks above.
4. Create the branch from the selected base:
   ```bash
   git switch -c <branch-name> <base>
   ```
   or, when branching directly from the fetched same-repo base:
   ```bash
   git switch --no-track -c <branch-name> origin/<base>
   ```
5. Verify:
   ```bash
   git branch --show-current
   ```

## Guardrails

- Do not overwrite, delete, reset, stash, or force anything.
- Do not switch to an existing branch without user intent.
- Do not create protected/shared base branches (`main`, `master`, `develop`, release branches) unless explicitly asked.
- Report any skipped freshness checks that could matter.
