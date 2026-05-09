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

Normalize `short-desc` with these rules:

- convert to lowercase
- replace spaces with `-`
- remove punctuation, symbols, and Chinese characters
- remove filler words that do not help distinguish the branch, such as `the`, `a`, `an`, `update`, `change`, `task`, `fix`, `issue`
- collapse repeated `-`
- trim leading/trailing `-`

## Workflow

1. Inspect repo guidance before naming the branch.
   - Check `CONTRIBUTING.md`
   - Check `.github/*` branch or workflow docs if present
   - Use the issue number from the user request, issue title, or existing task context
   - Fetch title/body with `gh issue view <issueID> --json title,body,number`
2. Choose the branch type from the work being started.
3. Build the branch name with the required format.
4. Create the branch with `git switch -c <branch-name>`.
5. Verify the branch with `git branch --show-current`.

## Validation

If the issue number is missing and the branch is temporary, create a clearly temporary name instead of inventing an IssueID.
If `gh issue view` fails, stop and request the issue details or fix GitHub CLI/authentication first.
