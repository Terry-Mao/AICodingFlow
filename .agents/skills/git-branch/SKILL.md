---
name: git-branch
description: Create branches that match the repo's naming rules, especially when a branch must include an IssueID or follow the type/short-desc format.
---

# git-branch

Create a working branch that follows repo naming and base-branch safety rules.

## Naming

- Check `CONTRIBUTING.md` and nearby Git guidance first.
- Issue-backed branch: `<type>/<short-desc>-<issueID>`.
- Non-issue branch: `<type>/<user-provided-name>`; do not invent an IssueID.
- Valid types: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`.
- Names must be lowercase, hyphen-separated, under 80 chars when possible, and
  must not use Chinese, uppercase letters, or multi-task descriptions.

For an IssueID, fetch `gh issue view <issueID> --json title,body,number`, derive
`short-desc` from the title, and fall back to body/task context only when
needed. If issue data cannot be fetched, use task context only when it is enough
and state that GitHub issue data was not verified.

For a non-issue branch, preserve a valid user-provided type prefix first, then
use an explicit valid type, then infer from task context, then default to
`chore` for a bare name. Do not override an explicit valid type.

Recognize IssueID from explicit wording, GitHub issue URLs, repo issue
shorthands, and branch-like issue references. If several issue numbers appear,
prefer the one explicitly described as the issue or task ID. Do not treat a PR
number as an IssueID unless the user says it is the task reference. See
`references/issue-id-examples.md`.

Normalize names by lowercasing; replacing spaces, underscores, and repeated
separators with `-`; removing punctuation, symbols, and Chinese characters
except the single `/` between type and name; removing filler words such as
`the`, `a`, `an`, `update`, `change`, `task`, `fix`, `issue`; collapsing
repeated `/` and `-`; trimming separators; and shortening to the smallest
meaningful phrase, preferably 2-5 words.

Validate with:

```bash
git check-ref-format --branch <branch-name>
```

## Safety

Before creating a branch, check:

```bash
git status --short
git branch --show-current
git branch --list <branch-name>
git branch --remotes --list "*/<branch-name>"
```

- If the worktree is dirty, ask whether to commit, stash, or continue.
- If the target branch exists, switch only after user confirmation.
- Prefer the repo's documented base, usually `main`, `master`, `develop`, or a
  release branch.
- For same-repo work, prefer `origin/<base>` over `upstream/<base>`; use
  `upstream` only for fork workflows or explicit repo guidance.
- Refresh the selected base when possible, for example `git fetch origin main`.
  If fetch is unavailable, report that freshness was not verified.
- Compare local and remote base with `git status -sb` or
  `git rev-list --left-right --count <base>...origin/<base>`. If local base is
  behind, ask whether to update it or branch directly from `origin/<base>`.
- If already on the target branch, do not recreate it.

## Create

After checks pass or the user approves continuing:

```bash
# From an up-to-date local base
git switch -c <branch-name> <base>

# Directly from a fetched remote base, without tracking the base
git switch --no-track -c <branch-name> origin/<base>
```

Do not make the feature branch track `origin/<base>`; `git-push` sets its
upstream when published.

Verify with:

```bash
git branch --show-current
```
