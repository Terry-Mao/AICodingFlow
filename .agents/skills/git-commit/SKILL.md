---
name: git-commit
description: Create focused, reviewable commits from the current diff without including unrelated files.
---

# git-commit

Use this when the user asks to commit current changes or organize them into
commits.

## Inspect and group

Review status, unstaged/staged diffs, and their stats. Check repository commit
conventions only when they are not already clear from the task or nearby files.
Split only genuinely separate concerns (for example behavior versus refactor,
dependency churn, generated output, formatting-only changes, or unrelated
docs/tests). Keep directly related tests with the change.

Stage only intended paths, using `git add -p` when a file contains mixed
concerns. Do not bulk-stage unrelated work.

## Message and commit

Unless repository conventions say otherwise, use:

```text
type(scope): summary
```

Use `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, or
`chore`. Add `Fixes #123` only for explicit closing intent or a clearly
completed narrow issue; use `Refs #123` for partial or ambiguous work. Never
invent issue IDs.

Run normal `git commit -m` so hooks execute. If a hook fails, stop and report;
do not use `--no-verify`, push, rewrite history, or force operations unless
explicitly requested. Report the final hash and whether hooks ran.
