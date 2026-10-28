---
name: create-pr
description: Create or update a review-ready GitHub pull request from the current branch.
---

# create-pr

Use this after `git-push` when the user asks to create, update, or open a pull
request. It prepares PR metadata; it does not implement code, commit, push, or
modify issues.

## Prepare

Inspect the current branch, worktree, and repository default PR base. A dirty
worktree must be intentionally excluded before continuing. Review the complete
base-to-head diff for accidental files, secrets, conflict markers, generated
churn, and missing validation. Sync the base into the branch when needed; if
that creates conflicts, resolve, validate, commit, and push the resolution.

Build a concise title and body from the issue, branch, commits, or user request.
Use a Conventional Commit title for the PR: `<type>[(scope)]: <description>`.
Choose the type from the actual change (for example, `feat`, `fix`, `docs`,
`refactor`, `test`, or `chore`); include a scope only when it clarifies the
change. Keep the description in the repository's prose language, for example
`fix(ci): 修复审查分发`. When updating a PR, keep an existing title if it follows
this format and still describes the complete diff; otherwise revise it.
Include `## Summary`, `## Testing`, `## Risk`, and `## How to revert`, plus a
known issue link (`Closes`, `Fixes`, or `Refs`). State actual test results,
the relevant risk and a concrete rollback action; never invent results or an
issue ID. Preserve any manually written sections when updating an open PR.
Before submitting, save the exact body and run
`python3 .github/scripts/validate_pr_body.py <body-file>`.

## Create or update

First check only for an open PR from the current branch. Do not use `gh pr view` as the existence check because it may resolve a previously merged or closed PR:

```bash
pr_url="$(gh pr list --state open --head "$branch" --json url --jq '.[0].url' --limit 1)"
```

If an open PR exists, read its current body, preserve manual content, and update it:

```bash
gh pr edit "$pr_url" --title "$title" --body-file "$body_file"
```

Otherwise create a new PR. A merged or closed PR with the same branch name is
not reusable:

```bash
gh pr create --base "$base" --head "$branch" --title "$title" --body-file "$body_file"
```

Pass generated values as separate quoted arguments; never interpolate untrusted
text into shell syntax. If `gh` is unavailable or unauthenticated, report the
exact base, head, title, and body for manual creation.

Report the PR URL, base/head, title, validation, and whether the base was synced.
