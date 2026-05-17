---
name: git-commit
description: Create clean, repo-aware commits from real diffs with focused inspection, selective staging, and minimal tool calls.
---

# git-commit

Commit current repo changes atomically, with accurate messages and no unrelated files.

## Inspect

Use one tool call for the common inspection:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
```

If staged output is empty, ignore it. Check repo message conventions only when unknown: prefer existing context, then obvious files such as `.gitmessage`, `CONTRIBUTING.md`, or commit config. Use recent history only when style is still unclear.

## Commit Boundaries

Split only for real separate concerns: behavior vs refactor, dependency churn vs code, generated output without source, formatting-only churn, or unrelated docs/tests. Keep directly related tests with the fix/feature.

Stage only intended paths:

```bash
git add <specific-files>
```

Use `git add -p` only when file-level staging would mix unrelated changes.

## Approval

If the user asked to commit a clear current change, proceed after inspection. Ask first only when included files, boundaries, risky content, or issue semantics are ambiguous. Keep questions short: included files, excluded files, proposed message, and the ambiguity.

## Message

Default format unless repo conventions say otherwise:

```text
type(scope): summary
```

Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`. Use a scope when obvious. Avoid `update`, `changes`, `misc`, and `wip`.

Issue links:

- Detect explicit user issue IDs first, then branch patterns like `<type>/<desc>-123`, `issue-123`, `gh-123`, or `#123`.
- Use `Fixes #123` only for explicit closing intent or a clearly complete narrow issue.
- Use `Refs #123` for partial, preparatory, docs-only, cleanup-only, or ambiguous work.
- Do not invent issue IDs.

## Commit

Use normal Git so hooks run:

```bash
git commit -m "<subject>"
```

If hooks fail, stop and report. Do not use `--no-verify`, push, rewrite history, or force anything unless explicitly asked.

Report the final commit hash and whether hooks/checks ran.
