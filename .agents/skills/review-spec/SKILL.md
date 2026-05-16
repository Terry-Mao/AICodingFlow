---
name: review-spec
description: Review a spec-only GitHub pull request from pinned `pr_diff.txt` and `pr_description.txt` snapshots, then write and validate `review.json` with document-quality findings.
---

# review-spec

Review one spec-only PR from two existing snapshot files:

- `pr_description.txt`: PR title, body, and metadata.
- `pr_diff.txt`: line-annotated PR diff.

Do not run `gh`, post comments, regenerate snapshots, or modify the spec files
being reviewed. The only output artifact is `review.json`.

## Purpose

Use this skill for PRs whose changed files are all under `specs/`, including
product specs, technical specs, design notes, plans, and similar planning
documents.

This skill reuses the core `review-pr` snapshot and output contract, but changes
the review lens from code defects to document quality.

## Inputs

Treat `pr_description.txt` and `pr_diff.txt` as the source of truth, even if the
PR changes later. This keeps review content, line numbers, base SHA, and head SHA
consistent.

`pr_diff.txt` uses the same `PR_DIFF_V1` format as `review-pr`. Inline comments
may target only `LEFT` or `RIGHT` lines present in `pr_diff.txt`; never target
`BOTH` context lines.

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

## Review Focus

Prioritize findings that would materially affect implementation, review quality,
or the ability to use the specs as source-of-truth planning documents.

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
reviewer's ability to evaluate the spec. Ignore personal writing preferences and
minor wording differences unless an exact `🧹 [NIT]` suggestion is available.

Always apply the repository's local
`.agents/skills/security-review-spec/SKILL.md` skill as a supplemental
high-level security pass on spec PRs. Fold any security findings into the same
`review.json` produced by this review rather than emitting a separate output.

## Out Of Scope

Do not review production-code concerns such as exception handling, performance,
API design details, test mocking style, or implementation correctness unless the
spec itself makes an incorrect, contradictory, or infeasible claim about them.

Do not request implementation changes. Review whether the document describes the
right behavior and a feasible plan.

Do not apply code-level review criteria such as error handling or low-level
performance to spec prose; the `security-review-spec` supplement covers
design-level security concerns.

## Local Companion

After applying this core workflow, read
`.agents/skills/review-spec-repo/SKILL.md` when it exists and apply any
non-conflicting repository-specific guidance.

The local companion may only supplement:

- required repository-specific spec sections
- `specs/` directory link conventions
- repository-specific format preferences

The local companion must not override:

- `review.json` structure
- severity labels
- safety rules
- evidence rules
- suggestion block format
- diff-line targeting rules
- validator requirements

## Inline Comment Rules

Start every inline comment body with exactly one label:

- `🚨 [CRITICAL]`: contradiction, severe omission, or spec issue likely to make
  implementation fail.
- `⚠️ [IMPORTANT]`: missing key detail, ambiguity, feasibility issue, or
  important mismatch with the issue or PR.
- `💡 [SUGGESTION]`: structure, clarity, or reviewability improvement.
- `🧹 [NIT]`: minor wording or format cleanup; must include a `suggestion` block.

Keep comments concise and actionable. Comment ranges must be 10 lines or fewer.

Use suggestion blocks only for exact replacements on `RIGHT` lines:

````markdown
```suggestion
replacement text
```
````

Do not use suggestions on `LEFT` lines. Omit `🧹 [NIT]` findings when no exact
suggestion is possible.

Put broad issues, cross-document issues, missing sections, and findings without
a precise changed-line target in top-level `body` instead of forcing an unrelated
inline comment.

## Output

Write `review.json` with exactly this shape:

```json
{
  "verdict": "APPROVE",
  "body": "Top-level review summary or issues that cannot be attached inline.",
  "comments": [
    {
      "path": "specs/example/product.md",
      "side": "RIGHT",
      "line": 42,
      "body": "⚠️ [IMPORTANT] concise finding..."
    }
  ]
}
```

Use `verdict: "APPROVE"` when there are no blocking-level document-quality
findings. Use `verdict: "REJECT"` when the spec has material gaps,
contradictions, missing acceptance criteria, infeasible technical direction, or
other problems that should be fixed before the plan is accepted. Keep the
top-level `body` wording consistent with the structured verdict.

For spec-only PRs, the workflow publishes both `APPROVE` and `REJECT` verdicts
as GitHub `COMMENT` reviews. A `REJECT` verdict is machine-readable review
state for the spec quality result; it does not become a GitHub blocking
`REQUEST_CHANGES` review and does not trigger the non-member human reviewer
request flow.

For ranges, add `start_line`:

```json
{
  "path": "specs/example/tech.md",
  "side": "RIGHT",
  "start_line": 40,
  "line": 42,
  "body": "💡 [SUGGESTION] concise finding...\n```suggestion\nreplacement\n```"
}
```

Constraints:

- `verdict` is required and must be `APPROVE` or `REJECT`.
- `body` is a string; use `""` when empty.
- `comments` is an array; use `[]` when there are no inline findings.
- Each comment has `path`, `side`, `line`, and `body`.
- `side` is `LEFT` or `RIGHT`.
- Inline targets must match changed `path/side/line` entries from `pr_diff.txt`.
- If `start_line` is present, the full range must be changed lines on the same
  `path` and `side`.
- Do not add unknown top-level fields. `recommended_reviewers` is allowed by the
  shared schema but should normally be omitted for spec-only reviews because the
  workflow does not request human reviewers for spec-only PRs.
- Do not wrap the whole JSON in markdown fences.

## Workflow

1. Read `pr_description.txt`.
2. Parse `pr_diff.txt`, build the allowed changed-line targets, and collect the
   changed file paths.
3. Apply the `specs/` scope guard from this skill.
4. Read `.agents/skills/review-spec-repo/SKILL.md` if present and apply only
   non-conflicting local guidance.
5. Read `.agents/skills/security-review-spec/SKILL.md` and apply it as a
   non-conflicting supplemental high-level security pass.
6. Inspect repository files only when needed to evaluate whether the specs are
   complete, aligned, feasible, or consistent.
7. Review the spec changes using the document-quality focus above and the
   supplemental security-review-spec guidance.
8. Write one combined `review.json` with `verdict`, `body`, and `comments`.
9. Run `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`.
10. Fix `review.json` until validation passes.
11. Finish with only the validated `review.json` content.

## Final Checks

- No `gh` commands were run.
- No GitHub comments were posted.
- No snapshots were regenerated.
- No spec files or production files were modified.
- `review.json` contains `verdict`, `body`, `comments`, and no unknown fields.
- `review.json` passed
  `.agents/skills/review-pr/scripts/validate_review_json.py`.
