---
name: review-pr-repo
specializes: review-pr
description: Repo-specific companion guidance for the core review-pr workflow. Do not use as the primary review entrypoint.
---

# review-pr-repo

This file is a companion to the core `review-pr` skill and
`.agents/contracts/review.md`.

Do not invoke this file as the primary review entrypoint. The primary entrypoint
is `.agents/skills/review-pr/SKILL.md`; that skill reads this companion when it
needs repository-specific review guidance.

This companion may add repository-specific checks and preferences, but it must
not override the core workflow, shared review contract, output schema, severity
labels, diff-line targeting, validation rules, or safety rules.

## Repository Review Focus

Prioritize findings that affect this repository's skills and PR-review automation:

- Skill files must be concise, operational, and safe for Codex to execute.
- Git helpers must avoid destructive operations, broad staging, unsafe force
  pushes, and accidental edits to user work.
- GitHub Actions review code must keep `pr_description.txt`, `pr_diff.txt`,
  and `review.json` stable and reproducible.
- Review automation must not call `gh`, post comments, fetch live PR state, or
  regenerate snapshots while the review skill is running.
- Repository-managed skill paths must use `.agents/skills/...`.
- Documentation examples must match the actual repository layout and commands.
- When multiple changed lines show the same root cause, prefer one actionable
  finding at the clearest line and mention the broader scope there.

## Self-Evolution Boundary

Future self-evolution should normally update this skill, not
`.agents/skills/review-pr/` or `.agents/contracts/review.md`. Treat core
review skill and shared contract changes as higher risk because they alter the
review contract used by CI.
