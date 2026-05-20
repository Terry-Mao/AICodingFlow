---
name: review-pr-repo
specializes: review-pr
description: Repo-specific wrapper around the core review-pr workflow for pull request reviews.
---

# review-pr-repo

Use this skill for reviewing pull requests in this repository.

This is a repository-local wrapper around the core `review-pr` skill. The core
skill remains authoritative for the workflow, snapshot contract, output schema,
severity labels, validation rules, and safety rules.

## Required Wrapper Flow

1. Read `.agents/skills/review-pr/SKILL.md`.
2. Follow the core `review-pr` workflow exactly.
3. Apply the repository-specific review focus below when choosing findings.

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
`.agents/skills/review-pr/`. Treat core `review-pr` changes as higher risk
because they alter the shared review contract used by CI.
