---
name: git-commit
description: Create clean, repo-aware git commits from real diffs with focused inspection and selective staging.
---

# git-commit

Use when committing changes, splitting work into commits, or drafting a commit message from actual repo changes.

## Goal

Create atomic, reviewable commits with accurate messages while avoiding unnecessary repo scans and repeated git output.

## Fast Workflow

1. Inspect the current diff:
   ```bash
   git status --short
   git diff --stat
   git diff
   ```
   If staged changes exist, also inspect:
   ```bash
   git diff --cached
   ```

2. Check repo conventions only as needed:
   - use known conversation context first;
   - otherwise inspect obvious local files such as `.gitmessage`, `CONTRIBUTING.md`, or commit config;
   - use recent history only when message style is unclear.

3. Decide commit boundaries from the diff. Split only when there are genuinely separate concerns, such as behavior vs refactor, dependency churn vs code, generated files without source changes, or unrelated docs/tests.

4. Stage only intended files:
   ```bash
   git add <specific-files>
   ```
   Use `git add -p` only when file-level staging would mix unrelated changes.

5. Commit with the normal Git path so configured hooks run:
   ```bash
   git commit -m "<subject>"
   ```
   If a hook fails, stop and report it. Do not use `--no-verify` unless explicitly asked.

## Approval

If the user explicitly asked to commit a clear set of current changes, proceed after inspection without a long proposal. Ask first only when boundaries are ambiguous, risky files are present, unrelated changes would be included, or the message/issue semantics are uncertain.

When asking, keep it short: files included, files excluded, proposed message, and the ambiguity.

## Message Rules

Default subject unless repo conventions say otherwise:

```text
type(scope): summary
```

Use a precise type: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, or `chore`. Prefer an obvious scope, keep the summary specific, and add a body only when the reason is not clear from the diff.

Avoid vague subjects such as `update`, `misc fixes`, `wip`, or `changes`.

## Issue Linking

Detect issue IDs from explicit user text first, then branch names like `<type>/<short-desc>-123`, `issue-123`, `gh-123`, or `#123`.

- Use `Fixes #123` only when the user requested closing behavior or the staged diff clearly completes a narrowly scoped issue.
- Use `Refs #123` for partial, preparatory, docs-only, cleanup-only, or ambiguous work.
- If no issue ID is found, do not invent one.

Follow any repo template if one is already known or easy to detect.

## Guardrails

- Inspect before staging or committing.
- Do not bulk-stage unrelated files.
- Do not commit secrets, credentials, conflict markers, local artifacts, accidental binaries, or unrelated changes.
- Do not auto-push, rewrite history, force-push, or bypass hooks unless explicitly asked.
- Report the final commit hash and whether hooks/checks ran.
