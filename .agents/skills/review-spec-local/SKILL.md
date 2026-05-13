---
name: review-spec-local
description: Repo-specific guidance for reviewing AICodingFlow spec changes.
---

# review-spec-local

Use this skill for reviewing PRs whose changed files are all under `specs/`.
When a PR mixes `specs/` files with non-spec files, `review-pr-local` may also
use this file as companion guidance for the `specs/` changes.

This is a repository-local wrapper around the core `review-pr` skill for
spec-only pull requests. The core skill remains authoritative for the workflow,
snapshot contract, output schema, severity labels, validation rules, and safety
rules.

## Required Wrapper Flow

1. Read `.agents/skills/review-pr/SKILL.md`.
2. Follow the core `review-pr` workflow exactly.
3. Apply the spec review focus below when choosing findings.

## Review Focus

- Check whether the spec is actionable enough for implementation work.
- Flag contradictions between requirements, examples, and acceptance criteria.
- Prefer top-level summary notes for broad product or process concerns that do
  not map cleanly to a changed line.

## Self-Evolution Boundary

`update-pr-review` may update this file from repeated human feedback on spec
reviews. Keep additions concise and evidence-backed.
