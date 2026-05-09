---
name: git-branch
description: Create branches that match the repo's naming rules, especially when a branch must include an IssueID or follow the type/short-desc format.
---

# git-branch

## Overview

Use this skill when you need to create a new working branch that must follow repository rules from `CONTRIBUTING.md` or nearby Git guidance.

## Branch Rules

- Prefer the repo's documented branch pattern.
- For this repo, formal development branches use `<type>/<short-desc>-<issueID>`.
- `type` should match Conventional Commits: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`.
- `short-desc` should be lowercase, brief, and hyphen-separated.
- Formal development branches must include an IssueID.
- Temporary test branches may omit the IssueID if the user explicitly wants a throwaway branch.
- Do not use Chinese, uppercase letters, or multi-task branch names.

## Branch Name Resolution

Use this order:

1. Read the IssueID from the user request or task context.
2. Use the GitHub CLI to fetch the issue data:
   - `gh issue view <issueID> --json title,body,number`
3. Derive `short-desc` from the issue title.
4. If the title is too short or too generic, fall back to the issue body/content fetched from GitHub.
5. If the issue cannot be fetched, ask for the missing data instead of inventing a branch name.

Do not accept a user-specified branch name as the primary source. The branch should be generated from the issue data so naming stays consistent.

Recognize IssueID from common user input forms, normalize it to the numeric issue number, and use that number for `gh issue view` and branch naming:

- plain number: `123`
- hash form: `#123`
- issue wording: `issue 123`, `issue #123`, `IssueID 123`, `IssueID: #123`
- GitHub issue URL: `https://github.com/<owner>/<repo>/issues/123`
- GitHub pull request URL when the user clearly identifies it as the task issue: `https://github.com/<owner>/<repo>/pull/123`
- repository shorthand: `<owner>/<repo>#123`
- branch-like references: `issue-123`, `issue/123`, `<type>/<short-desc>-123`

If several issue numbers appear, prefer the one explicitly described as the issue or task ID. If the intended issue is ambiguous, ask the user to choose instead of guessing.

Normalize `short-desc` with these rules:

- convert to lowercase
- replace spaces with `-`
- remove punctuation, symbols, and Chinese characters
- remove filler words that do not help distinguish the branch, such as `the`, `a`, `an`, `update`, `change`, `task`, `fix`, `issue`
- collapse repeated `-`
- trim leading/trailing `-`

## Safety Checks

Before running `git switch -c <branch-name>`, verify the local repository state:

- Check for uncommitted changes with `git status --short`. If the worktree is dirty, stop and ask whether to commit, stash, or continue from the current state.
- Check whether the target branch already exists with `git branch --list <branch-name>` and `git branch --remotes --list "*/<branch-name>"`. If it exists, switch to it only after the user confirms that is intended.
- Check the current branch with `git branch --show-current`. Prefer creating formal development branches from the repo's documented base branch, usually `main`, `master`, `develop`, or a release branch named by repo guidance.
- If the current branch is not a suitable base, ask whether to switch to the expected base before creating the new branch.
- If the repo has a remote and network access is available, run `git fetch --prune` before checking whether the base branch is current. If fetching is unavailable or not allowed, tell the user the base freshness was not verified.
- Compare the local base with its upstream using `git status -sb` or `git rev-list --left-right --count <base>...<upstream>`. If the base is behind, ask whether to update it before branching.

## Workflow

1. Inspect repo guidance before naming the branch.
   - Check `CONTRIBUTING.md`
   - Check `.github/*` branch or workflow docs if present
   - Detect and normalize the issue number from the user request, issue title, or existing task context
   - Fetch title/body with `gh issue view <issueID> --json title,body,number`
2. Choose the branch type from the work being started.
3. Build the branch name with the required format.
4. Run the safety checks for uncommitted changes, existing branches, base branch suitability, and base freshness.
5. Create the branch with `git switch -c <branch-name>` only after the checks pass or the user explicitly approves continuing.
6. Verify the branch with `git branch --show-current`.

## Validation

If the issue number is missing and the branch is temporary, create a clearly temporary name instead of inventing an IssueID.
If `gh issue view` fails, stop and request the issue details or fix GitHub CLI/authentication first.
If the target branch exists, the worktree is dirty, the current base looks wrong, or the base may be stale, pause and resolve that condition before creating a new formal development branch.
