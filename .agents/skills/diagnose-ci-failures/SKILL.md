---
name: diagnose-ci-failures
description: Diagnose CI failures for a PR, branch, run ID, or GitHub Actions run URL using the GitHub CLI, extract error logs, and generate a plan to fix them. Use when the user asks to check CI status, pull CI issues, triage test failures, or investigate PR build failures.
---

# diagnose-ci-failures

Programmatically diagnose CI failures and generate a plan to fix them.

## Overview

This skill provides a deterministic workflow to check CI status, extract failure logs, analyze errors, and create a plan to resolve issues. The output is always a plan document that can be reviewed before execution.

This skill is diagnosis-only. Do not make code changes, commits, pushes, or pull requests.

## Workflow

### 1. Locate the failing CI target

Determine the CI target from the user's input.

If the user provides a GitHub Actions run URL, extract the run ID from the URL:

```bash
gh run view <run-id> --verbose
```

Example URL:

```text
https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

If the user provides a run ID directly:

```bash
gh run view <run-id> --verbose
```

If the user provides a branch name:

```bash
gh run list --branch <branch> --status failure --limit 5
gh run view <run-id> --verbose
```

If no branch, run ID, or URL is provided, use the current checkout. First check whether the current branch has an associated PR:

```bash
gh pr view --json number,title,url,state,statusCheckRollup
```

For a current PR branch, list failed PR checks:

```bash
gh pr view --json statusCheckRollup --jq '.statusCheckRollup[] | select(.conclusion == "FAILURE")'
```

If the current branch does not have an associated PR, fall back to recent failed workflow runs for the current branch:

```bash
git branch --show-current
gh run list --branch <branch> --status failure --limit 5
gh run view <run-id> --verbose
```

If no failed PR check or failed workflow run exists, report that no failing CI target was found and stop.

### 2. Check CI status

Fetch the status of all CI checks for the selected PR, branch, or run.

For a PR branch:

```bash
gh pr view --json statusCheckRollup
```

For a workflow run:

```bash
gh run view <run-id> --verbose
```

Parse the output to identify:

- Completed checks
- In-progress checks
- Successful checks
- Failed checks, including names, run IDs, job IDs, and details URLs when available

If CI is still running, inform the user which checks have already failed or passed, highlight checks still running, and suggest waiting for completion before final diagnosis.

### 3. Extract failure logs

For each failed run or failed check, pull failed-step logs:

```bash
gh run view <run-id> --log-failed
```

For deeper inspection when needed:

```bash
gh run view <run-id> --log --job <job-id>
gh run download <run-id> -D .artifacts/<run-id>
```

Focus on extracting:

- Error messages and locations, including file paths and line numbers
- Build or compilation errors
- Linting or formatting failures
- Test failure messages, failing test names, stack traces, and assertion output
- Environment or CI setup failures, such as missing secrets, permissions, unavailable services, dependency installation failures, or resource limits

### 4. Categorize errors

Group errors by type:

- **Build/compilation errors**: Type errors, syntax errors, missing imports, missing dependencies, incompatible versions, failed builds
- **Test failures**: Failing tests, assertion failures, snapshot mismatches, timeouts, integration failures, flaky-looking behavior
- **Linting/formatting issues**: Formatter failures, linter violations, unused code, style violations
- **Environment issues**: Missing secrets, permissions, unavailable services, CI image problems, dependency download failures, resource limits, platform-specific setup issues

When tools are language-specific, mention them only as observed facts from the logs, not as assumptions.

### 5. Generate fix plan

Create a plan document with:

- **Problem Statement**: Summary of failing checks or workflow runs
- **Current State**: What errors were found, where they occur, and which checks are affected
- **Root Cause Analysis**: The most likely cause of each failure category, based on the logs
- **Proposed Changes**: Specific fixes needed for each error category
- **Validation Steps**: Commands or CI checks that should be run to verify the fixes

Do not implement the fixes. The plan should be specific enough for a follow-up implementation task.

## Important Notes

- Always create a plan first. Never make code changes directly.
- Prefer evidence from CI logs over local assumptions.
- If tests fail locally but pass in CI, treat them as local/environment-specific unless CI logs show the same failure.
- If CI logs show multiple unrelated failures, group them and recommend fixing one category at a time.
- Avoid assuming a programming language, package manager, test framework, or build system until it is observed from repository files or CI logs.

## Common CI Check Types

- Formatting and linting
- Unit tests
- Integration tests
- Build or package checks
- Platform-specific tests
- Deployment or artifact checks
- CI summary or required-status checks

## Example Commands

Get failed checks for the current PR branch:

```bash
gh pr view --json statusCheckRollup --jq '.statusCheckRollup[] | select(.conclusion == "FAILURE")'
```

Get recent failed runs for a branch:

```bash
gh run list --branch <branch> --status failure --limit 5
```

Inspect a specific run:

```bash
gh run view <run-id> --verbose
```

Get failed logs from a specific run:

```bash
gh run view <run-id> --log-failed
```

Inspect a specific failed job:

```bash
gh run view <run-id> --log --job <job-id>
```
