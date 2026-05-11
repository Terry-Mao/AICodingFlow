---
name: review-spec-local
description: Repo-specific companion guidance for reviewing AICodingFlow spec-only pull requests.
---

# review-spec-local

Use this companion for PRs whose changed files are all under `specs/`.

Keep this file focused on repository-specific spec review preferences. Do not
define or override core review schema, severity labels, diff-line targeting, or
validation rules.

## Review Focus

- Check whether the spec is actionable enough for implementation work.
- Flag contradictions between requirements, examples, and acceptance criteria.
- Prefer top-level summary notes for broad product or process concerns that do
  not map cleanly to a changed line.

## Self-Evolution Boundary

`update-pr-review` may update this file from repeated human feedback on spec
reviews. Keep additions concise and evidence-backed.
