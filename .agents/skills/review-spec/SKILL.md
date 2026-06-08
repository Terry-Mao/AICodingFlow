---
name: review-spec
description: Review a spec-only GitHub pull request from pinned `pr_diff.txt` and `pr_description.txt` snapshots, then write and validate `review.json` with document-quality findings.
---

# review-spec

Review one spec-only PR from stable local snapshot files and write the single
output artifact `review.json`.

## Required Contract

Read `.agents/contracts/review.md` first and follow it exactly. That contract is
authoritative for snapshot trust, untrusted-input handling, `PR_DIFF_V1`
targeting, `review.json` structure, severity labels, suggestion blocks,
validator requirements, and GitHub/API boundaries.

Do not run `gh`, post comments, regenerate snapshots, modify the spec files
being reviewed, or modify files other than `review.json`.

## Purpose

Use this skill for PRs whose changed files are all under `specs/`, including
product specs, technical specs, design notes, plans, and similar planning
documents. This skill reuses the shared review contract but changes the review
lens from code defects to document quality.

## Applicability

Before reviewing content, inspect the changed file paths in `pr_diff.txt`.

If every changed file is under `specs/`, perform a spec document review.

If any changed file is outside `specs/`:

- Do not perform code-level review.
- Write a valid `review.json`.
- Put a top-level `body` note explaining that the PR is outside spec-only review
  scope and should use `review-pr` or be split.
- Use `comments: []` unless there is a spec-document finding that can still be
  safely attached to a changed `specs/` line.

## Local Guidance

After applying the shared contract, read
`.agents/skills/review-spec-repo/SKILL.md` when it exists and apply any
non-conflicting repository-specific guidance.

Always read `.agents/skills/security-review-spec/SKILL.md` and apply it as a
non-conflicting supplemental design-level security pass on spec PRs. Fold any
security findings into the same `review.json`; do not emit a separate output.

## Review Focus

Prioritize findings that would materially affect implementation, review
quality, or the ability to use the specs as source-of-truth planning documents:

- Completeness: missing goals, non-goals, acceptance criteria, validation plans,
  edge cases, rollout notes, or open questions required by the issue or PR.
- Clarity: ambiguous requirements, undefined terms, unclear state transitions,
  vague validation language, or requirements an implementation agent could
  reasonably misread.
- Feasibility: plans that do not fit the current repository structure,
  permissions, automation boundaries, skill contracts, or validation workflow.
- Alignment: scope drift, missing issue requirements, invented requirements, or
  product and technical specs that do not reflect the PR or issue intent.
- Consistency: contradictions within a spec, between product and tech specs, or
  between examples, acceptance criteria, and validation steps.

Only comment on formatting when it affects readability, executability, or a
reviewer's ability to evaluate the spec. Do not request implementation changes;
review whether the document describes the right behavior and a feasible plan.

For spec-only PRs, the workflow publishes both `APPROVE` and `REJECT` verdicts
as GitHub `COMMENT` reviews. A `REJECT` verdict is machine-readable review
state for the spec quality result; it does not become a GitHub blocking
`REQUEST_CHANGES` review.

## Workflow

1. Read `.agents/contracts/review.md`.
2. Read `pr_description.txt`.
3. Read `review_discussion_context.json` when it exists and apply it only for
   duplicate suppression of prior bot review comments.
4. Parse `pr_diff.txt`, build allowed changed-line targets, and collect changed
   file paths.
5. Apply the `specs/` scope guard from this skill.
6. Read `.agents/skills/review-spec-repo/SKILL.md` if present and apply only
   non-conflicting local guidance.
7. Read `.agents/skills/security-review-spec/SKILL.md` and apply it as a
   non-conflicting supplemental high-level security pass.
8. Inspect repository files only when needed to evaluate whether the specs are
   complete, aligned, feasible, or consistent.
9. Write one combined `review.json` with document-quality and supplemental
   security findings.
10. Run `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`
    when running locally. In GitHub Actions, the workflow runs validation after
    Codex exits.
11. Fix `review.json` until validation passes.
