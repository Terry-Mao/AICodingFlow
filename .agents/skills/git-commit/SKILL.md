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

4. **Propose and approve**
   Before committing, show:
   - what changed
   - recommended commit boundary or boundaries
   - candidate commit message(s)
   - risks / ambiguities
   - any repo-specific template or format that will be followed

   Get user approval before staging or committing when boundaries are not already explicit.

5. **Stage selectively**
   Prefer:
   ```bash
   git add <specific-files>
   ```
   Do not default to bulk staging. Stage only the intended files.
   Use `git add -p` only when file-level staging is too broad and hunk-level staging is required.

6. **Validate deterministically**
   If the repository has configured a native `git` pre-commit hook, it must run during commit creation.
   This is mandatory when configured; do not skip validation unless the user explicitly asks to commit without verification.
   Use the normal `git commit` path so Git invokes the configured hook automatically.
   If validation fails, stop and report the failure without retrying with `--no-verify` unless the user explicitly asks.
   If no pre-commit hook is configured, say so explicitly instead of implying the check ran.

7. **Commit**
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

Detect issue ID in this order:

1. **User mention** - if the user explicitly says "fix #123" or "closes #456", use that.
2. **Branch name** - extract from common patterns:
   - `<type>/<short-desc>-<issueID>` such as `fix/http-bug-4`
   - `<type>/<short-desc>-gh-<issueID>` such as `fix/http-bug-gh-4`
   - `fix-123-xxx`, `123-fix-xxx`
   - `issue-123`, `issue/123`
   - `GH-123`, `gh-123`
   - `#123` anywhere in branch name

Choose the link format from repo conventions:

- If the repo template expects a footer, place the issue reference in the footer.
- If the repo template expects inline linking, prefer: `fix(scope): description (#123)`
- If no template is present, use a footer.
- Use `Fixes #123` only when the commit should close the issue.
- Use `Refs #123` when the commit is related, partial, preparatory, docs-only, tests-only, cleanup-only, or ambiguous.

Use auto-close semantics only when there is explicit closing intent or clear local evidence:

- The user explicitly asks for closing behavior, such as "fixes #123", "closes #123", "resolves #123", "close the issue", or "this completes #123".
- The issue title/body or task context clearly describes a bug and the staged diff directly fixes that bug.
- The commit is the final implementation for a narrowly scoped issue, and the user or issue context makes completion unambiguous.

Do not infer `Fixes` from a branch issue ID, `fix/...` branch, or `fix(...)` subject alone.

If no issue ID is found, do not invent one. If the user rejects the detected ID, defer to the user.
When unsure, use `Refs #123` and mention the uncertainty before committing.

## Guardrails

- Inspect before staging or committing.
- Keep one logical change per commit.
- Keep fix + directly related tests together.
- Split unrelated refactors, formatting, dependency churn, and generated noise.
- Report validation status and whether the native `git` pre-commit hook actually ran.
- Report the final commit hash after a successful commit.
- Do not auto-push, auto-force-push, rewrite history, or use `--no-verify` unless explicitly asked.
- Do not commit secrets, credentials, conflict markers, local artifacts, accidental binaries, or unrelated changes.
- Do not claim checks passed when they were not run.

## Default response shape

Before committing, summarize changed/staged/unstaged/untracked files, mixed concerns, risky files, proposed commit message(s), what each commit includes/excludes, and ask for approval when needed.

## Reference

See `references/commit-examples.md` for message examples, boundary patterns, and issue-linking examples.
