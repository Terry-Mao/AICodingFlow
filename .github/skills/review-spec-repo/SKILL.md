---
name: review-spec-repo
specializes: review-spec
description: Repo-specific companion guidance for the core review-spec workflow. Do not use as the primary spec review entrypoint.
---

# review-spec-repo

This file is a companion to the core `review-spec` skill and
`.agents/contracts/review.md`.

Do not invoke this file as the primary spec review entrypoint. The primary
entrypoint is `.github/skills/review-spec/SKILL.md`; that skill reads this
companion when it needs repository-specific spec review guidance.

This companion may add repository-specific checks and preferences, but it must
not override the core workflow, shared review contract, output schema, severity
labels, diff-line targeting, validation rules, or safety rules.

## Review Focus

- Check whether the spec is actionable enough for implementation work.
- Flag contradictions between requirements, examples, and acceptance criteria.
- Prefer top-level summary notes for broad product or process concerns that do
  not map cleanly to a changed line.

## Self-Evolution Boundary

`update-pr-review` may update this file from repeated human feedback on spec
reviews. Keep additions concise and evidence-backed. Do not use this file to
override `.agents/contracts/review.md`.
