---
name: git-branch
description: Create branches that match the repo's naming rules, especially when a branch must include an IssueID or follow the type/short-desc format.
---

# git-branch

## Overview

Use this skill when you need to create a new working branch that must follow repository rules from `CONTRIBUTING.md` or nearby Git guidance.

For issue-backed development, use this skill first to resolve the issue and create the branch, then implement the change and use `git-commit` after code changes are complete.

## Branch Rules

- Prefer the repo's documented branch pattern.
- Issue-backed branches use `<type>/<short-desc>-<issueID>`.
- Branches without a recognized IssueID use `<type>/<user-provided-name>` and must not invent or append an IssueID.
- `type` should match Conventional Commits: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`.
- `short-desc` should be lowercase, brief, and hyphen-separated.
- Keep branch names under 80 characters when possible.
- Do not use Chinese, uppercase letters, or multi-task branch names.

## Branch Name Resolution

Inspect repo guidance relevant to branch naming before choosing a name. Then choose one path:

1. **IssueID recognized**
   - Fetch issue data with `gh issue view <issueID> --json title,body,number`.
   - Derive `short-desc` from the issue title, falling back to the body when the title is too short, too generic, or normalizes to an empty value.
   - Build `<type>/<short-desc>-<issueID>`.
   - Do not use a user-specified branch name as the primary source for issue-backed work. If issue data is unusable and the user supplied a better description, use it only as `short-desc` and keep the issue number.
   - If the issue cannot be fetched, use the request/task context only when it is enough to name the branch and understand the work. State that GitHub issue data was not verified. Otherwise ask for the missing issue title, task summary, or GitHub CLI/authentication fix.
2. **No IssueID recognized**
   - Use the user-provided branch name as the primary source.
   - Normalize it with the same branch-name rules.
   - Do not ask for issue details.
   - Build `<type>/<user-provided-name>`.

Resolve `type` for a user-provided branch name without an IssueID in this order:

1. Preserve a valid type prefix when the user provides a full branch name, such as `fix/login-error`.
2. Use an explicitly requested type when the user separates it from the name, such as "type is fix, branch name is login-error" or "create fix branch login-error".
3. Infer the type from the requested work when the user provides only a bare name and task context.
4. Use `chore` when the request is only a bare branch name and no type or task context is available.

Do not override an explicitly requested valid type just because the inferred task category is different. If the requested type is invalid, normalize only when the intended valid type is obvious; otherwise ask for clarification.

Recognize IssueID from explicit user wording, GitHub issue URLs, repository issue shorthands, and branch-like issue references.
If several issue numbers appear, prefer the one explicitly described as the issue or task ID. If the intended issue is ambiguous, ask the user to choose instead of guessing.
Do not treat a pull request number as an IssueID unless the user explicitly says that PR is the task reference.
See `references/issue-id-examples.md` for recognized IssueID examples.

Normalize names with these rules:

- convert to lowercase
- replace spaces, underscores, and repeated separators with `-`
- remove punctuation, symbols, and Chinese characters, except the single `/` between `type` and branch name
- remove filler words that do not help distinguish the branch, such as `the`, `a`, `an`, `update`, `change`, `task`, `fix`, `issue`
- collapse repeated `/` and `-`
- trim leading/trailing `/` and `-`
- shorten long descriptions to the smallest meaningful phrase, preferably 2-5 words
- verify the final branch name with `git check-ref-format --branch <branch-name>`

## Safety Checks

Before running `git switch -c <branch-name>`, verify the local repository state:

- Check for uncommitted changes with `git status --short`. If the worktree is dirty, stop and ask whether to commit, stash, or continue from the current state.
- Check whether the target branch already exists with `git branch --list <branch-name>` and `git branch --remotes --list "*/<branch-name>"`. If it exists, switch to it only after the user confirms that is intended.
- Check the current branch with `git branch --show-current`. Prefer creating development branches from the repo's documented base branch, usually `main`, `master`, `develop`, or a release branch named by repo guidance.
- If the current branch is not a suitable base, ask whether to switch to the expected base before creating the new branch.
- For same-repository development, prefer `origin/<base>` over `upstream/<base>`. Use `upstream` only for fork workflows or explicit repo guidance.
- If the repo has a remote and network access is available, refresh the selected base before checking freshness. For the default `main` base, run `git fetch origin main`. If fetching is unavailable or not allowed, tell the user the base freshness was not verified.
- Compare the local base with `origin/<base>` using `git status -sb` or `git rev-list --left-right --count <base>...origin/<base>`. If the local base is behind, ask whether to update it before branching. If creating directly from `origin/<base>`, report that the local base branch was not updated.
- If already on the target branch, do not recreate it; report that the branch is already active.

## Workflow

1. Inspect repo guidance before naming the branch.
   - Check `CONTRIBUTING.md`
   - Check `.github/*` branch or workflow docs if present
   - Detect and normalize the issue number from the user request, issue title, or existing task context
   - Fetch title/body with `gh issue view <issueID> --json title,body,number` only when an IssueID is recognized
2. Choose the branch type from the work being started or from the user's explicit type:
   - `feat` for new user-visible behavior
   - `fix` for bug fixes
   - `docs` for documentation-only changes
   - `test` for test-only changes
   - `refactor`, `perf`, or `chore` only when those are the clearest purpose
3. Build the branch name, using the issue-backed format when an IssueID is recognized and `<type>/<user-provided-name>` otherwise.
4. Validate the final branch name with `git check-ref-format --branch <branch-name>`.
5. Run the safety checks for uncommitted changes, existing branches, base branch suitability, and base freshness.
6. Create the branch only after the checks pass or the user explicitly approves continuing. Prefer `git switch -c <branch-name> <base>` from an up-to-date local base; use `git switch -c <branch-name> origin/<base>` when intentionally branching from the fetched remote base without updating the local base. Do not make the new feature branch track `origin/<base>`; `git-push` sets its upstream when published.
7. Verify the branch with `git branch --show-current`.

## Validation

If the target branch exists, the worktree is dirty, the current base looks wrong, or the base may be stale, pause and resolve that condition before creating a new development branch.
