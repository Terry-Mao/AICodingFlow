---
name: diagnose-ci-failures
description: Diagnose a PR, branch, run, or GitHub Actions URL from CI evidence and produce a fix plan without changing code.
---

# diagnose-ci-failures

Use this when the user asks to inspect failing CI. This skill is diagnosis-only:
it produces a reviewable plan and does not edit, commit, push, or create PRs.

## Find and inspect the target

Use the user's run URL, run ID, or branch when provided. Otherwise inspect the
current branch's PR and failed checks, then fall back to recent failed runs for
that branch. If no failing target exists, report that and stop.

```bash
gh run view <run-id> --verbose
gh run list --branch <branch> --status failure --limit 5
gh pr view --json number,title,url,state,statusCheckRollup
```

For the selected PR/run, identify completed, pending, passed, and failed checks.
If checks are still running, report the partial state instead of guessing.
Pull failed-step logs first:

```bash
gh run view <run-id> --log-failed
```

Inspect a specific job or download artifacts only when the failed-step output is
insufficient. Extract observed paths, line numbers, error messages, failing
tests, stack traces, and environment/permission failures.

## Produce the plan

Group evidence into build/compile, test, lint/format, and environment/setup
failures. Do not assume a language, tool, or root cause before repository files
or logs establish it. Write a plan containing:

- problem statement and affected checks;
- current evidence and locations;
- likely root cause grounded in the logs;
- specific proposed changes;
- validation steps for the follow-up implementation.

Prefer CI evidence over local guesses. Treat multiple unrelated failures as
separate categories and recommend resolving them one category at a time.
