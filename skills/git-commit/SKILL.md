---
name: git-commit
description: Create clean, repo-aware git commits from real diffs. Use when committing changes, splitting mixed work, or drafting commit messages from an actual diff.
---

# git-commit

Use this when the user asks to commit changes, split work into commits, or write a good commit message from actual repo changes.

## Goal

Atomic, reviewable, semantically clear commits that are safe to revert, cherry-pick, and bisect.
This skill is language-agnostic: decide commit boundaries from the diff and repository conventions, not from the programming language.

## Core workflow

1. **Discover repo conventions**
   Check for repository-specific commit guidance before proposing a message.
   Prefer, in order:
   - `.github/*` files that describe commit style, templates, or issue linking
   - `.gitmessage`
   - `CONTRIBUTING.md`
   - `commitlint` / conventional commit config
   - recent commit history

2. **Inspect**
   Run:
   ```bash
   git status --short
   git diff --stat
   git diff
   ```
   If anything is staged, also run:
   ```bash
   git diff --cached
   ```

3. **Group**
   Split changes by logical purpose.

   Common groups:
   - `feat`
   - `fix`
   - `refactor`
   - `perf`
   - `docs`
   - `test`
   - `build` / `ci` / `chore`

   Usually split when you see:
   - refactor + behavior change
   - formatting + logic change
   - dependency updates + product code
   - unrelated docs + code
   - generated churn without clear source change

4. **Propose**
   Before committing, show:
   - what changed
   - recommended commit boundary or boundaries
   - candidate commit message(s)
   - risks / ambiguities
   - any repo-specific template or format that will be followed

5. **Approve**
   Get user approval before staging or committing when boundaries are not already explicit.

6. **Stage selectively**
   Prefer:
   ```bash
   git add -p
   ```
   Do not default to bulk staging. Stage only the intended hunks.

7. **Validate deterministically**
   If the repository has configured a native `git` pre-commit hook, it must run before creating the commit.
   This is mandatory when configured; do not skip validation unless the user explicitly asks to commit without verification.
   Use the normal `git commit` path so Git invokes the configured hook automatically.
   If validation fails, stop and report the failure before committing.
   If no pre-commit hook is configured, say so explicitly instead of implying the check ran.

8. **Commit**
   Commit only after the above steps are satisfied.

## Commit message rules

Default subject format unless repository conventions say otherwise:
```text
type(scope): summary
```

Examples:
- `fix(router): avoid nil worker panic during reconnect`
- `refactor(runtime): split worker lifecycle management`
- `docs(skill): simplify git commit instructions`

Guidelines:
- Use the most precise type possible.
- Prefer a real scope when obvious; otherwise omit it.
- Keep the summary short and specific.
- Use a body only when the why is non-obvious.
- Avoid vague subjects like `update`, `misc fixes`, `wip`, or `changes`.

## Issue linking

Detect issue ID from (in priority order):

1. **User mention** - if the user explicitly says "fix #123" or "closes #456", use that
2. **Branch name** - extract from common patterns:
   - `<type>/<short-desc>-<issueID>` such as `fix/http-bug-4`
   - `fix-123-xxx`, `123-fix-xxx`
   - `issue-123`, `issue/123`
   - `GH-123`, `gh-123`
   - `#123` anywhere in branch name

Formats:
- If the repo template expects a footer, prefer: `Fixes #123`
- If the repo template expects inline linking, prefer: `fix(scope): description (#123)`
- If no template is present, prefer a footer when auto-close semantics are desired

If no issue ID is found, do not invent one. If the user rejects the detected ID, defer to the user.

Always:
- inspect before staging or committing
- keep one logical change per commit
- keep fix + directly related tests together
- split unrelated refactors, formatting, dependency churn, and generated noise
- report validation status and whether the native `git` pre-commit hook actually ran

Never:
- commit blindly
- assume all modified files belong together
- auto-push, auto-force-push, or rewrite history unless explicitly asked
- commit secrets, credentials, conflict markers, local artifacts, or accidental binaries
- claim checks passed when they were not run

## Default response shape

Before committing, respond roughly like this:

### Commit analysis
- changed files
- staged files
- unstaged files
- untracked files
- mixed concerns
- risky files

### Proposed commit plan
1. `<type(scope): summary>`
   - includes
   - excludes
   - rationale

### Approval
Ask the user to confirm before staging or committing.

## Reference

See `references/commit-examples.md` for message examples, boundary patterns, and issue-linking examples.
