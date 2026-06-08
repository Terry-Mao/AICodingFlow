---
name: review-pr
description: Review a GitHub pull request from pinned `pr_description.txt`, `pr_diff.txt`, and optional `spec_context.md` snapshots, then write and validate `review.json`. Use when a CI job or bot needs offline PR review comments without posting to GitHub.
---

# review-pr

Review one code or mixed-content PR from stable local snapshot files and write
the single output artifact `review.json`.

## Required Contract

Read `.agents/contracts/review.md` first and follow it exactly. That contract is
authoritative for snapshot trust, untrusted-input handling, `PR_DIFF_V1`
targeting, `review.json` structure, severity labels, suggestion blocks,
validator requirements, and GitHub/API boundaries.

Do not run `gh`, post comments, regenerate snapshots, or modify files other
than `review.json`.

## Applicability

Use this skill for PRs where implementation correctness, security, error
handling, performance, maintainability, tests, or docs-vs-code consistency need
review.

For docs-only PRs outside `specs/`, review whether the docs match code,
examples, defaults, behavior, and validation instructions. Do not invent
implementation findings when the diff only changes documentation.

## Local Guidance

After applying the shared contract, read `.agents/skills/review-pr-repo/SKILL.md`
when it exists and apply any non-conflicting repository-specific guidance.

When `spec_context.md` exists, read
`.agents/skills/check-impl-against-spec/SKILL.md` and treat material spec drift
as a review concern.

Always read `.agents/skills/security-review-pr/SKILL.md` and apply it as a
non-conflicting supplemental security pass on code and mixed PRs. Fold any
security findings into the same `review.json`; do not emit a separate output.

## Review Focus

Prioritize concrete findings:

- correctness defects
- security risks
- exception and error handling gaps
- performance risks
- maintainability issues with clear impact
- documentation changes that disagree with code, examples, defaults, or behavior
- test changes that miss important assertions, over-mock behavior, or skip risky paths

Ignore pure style unless you can provide an exact GitHub `suggestion`. Put
issues that cannot be attached to changed lines, such as missing tests or docs,
in top-level `body`.

## Evidence Rules

Ground every finding in changed lines, nearby unchanged context from
`pr_diff.txt`, `spec_context.md`, `review_discussion_context.json`, or
repository files you actually inspected.

Do not request broad refactors or speculative changes unless the diff
introduces a concrete risk. If the impact is uncertain, lower the severity or
omit the finding.

If a concern involves untouched code or missing work that has no precise changed
line target, mention it in top-level `body` instead of attaching it to an
unrelated line.

## Workflow

1. Read `.agents/contracts/review.md`.
2. Read `pr_description.txt`.
3. Read `spec_context.md` when it exists.
4. Read `review_discussion_context.json` when it exists and apply it only for
   duplicate suppression of prior bot review comments.
5. Parse `pr_diff.txt`, build allowed changed-line targets, and collect changed
   file paths.
6. Read `.agents/skills/review-pr-repo/SKILL.md` if present and apply only
   non-conflicting local guidance.
7. If `spec_context.md` exists, read
   `.agents/skills/check-impl-against-spec/SKILL.md` and apply it as
   non-conflicting local guidance.
8. Read `.agents/skills/security-review-pr/SKILL.md` and apply it as a
   non-conflicting supplemental security pass.
9. Inspect relevant repository files only when needed to understand changed code
   or verify a concrete risk.
10. Write one combined `review.json` that includes base review findings and any
    supplemental security findings.
11. Run `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`
    when running locally. In GitHub Actions, the workflow runs validation after
    Codex exits.
12. Fix `review.json` until validation passes.
