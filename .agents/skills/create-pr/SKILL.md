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
Include summary, validation, and a known issue link (`Closes`, `Fixes`, or
`Refs`). Never invent an issue ID.

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
