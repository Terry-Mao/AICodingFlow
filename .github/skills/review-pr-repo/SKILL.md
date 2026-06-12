---
name: review-pr-repo
specializes: review-pr
description: Repo-specific companion guidance for the core review-pr workflow. Do not use as the primary review entrypoint.
---

# review-pr-repo

This file is a companion to the core `review-pr` skill and
`.agents/contracts/review.md`.

Do not invoke this file as the primary review entrypoint. The primary entrypoint
is `.github/skills/review-pr/SKILL.md`; that skill reads this companion when it
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
- Local/shared skill paths must use `.agents/skills/...`; GitHub workflow-only
  skill paths must use `.github/skills/...`.
- Before flagging a referenced path as missing, account for files or directories
  added, deleted, or renamed within the same PR diff; workflow prompts may point
  at the post-merge path introduced by that PR.
- Documentation examples must match the actual repository layout and commands.
- When `docs/product/wiki/` compiled content changes durable product or workflow
  facts, verify the authoritative `docs/product/raw/` source in the same PR
  supports the new fact; do not require raw changes for wiki-only recompiles
  that merely reflect already-updated raw sources.
- Validators and report checks that parse `#<number>` references should
  distinguish issue references from PR/source references and enforce issue URL
  requirements only in an explicit issue or related-issue context.
- When multiple changed lines show the same root cause, prefer one actionable
  finding at the clearest line and mention the broader scope there.

## Self-Evolution Boundary

Future self-evolution should normally update this skill, not
`.github/skills/review-pr/` or `.agents/contracts/review.md`. Treat core
review skill and shared contract changes as higher risk because they alter the
review contract used by CI.
