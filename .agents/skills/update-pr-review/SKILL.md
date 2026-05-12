---
name: update-pr-review
description: Improve repo-local PR review companion skills from human feedback on bot reviews. Use when updating AICodingFlow review guidance from recent GitHub PR review feedback.
---

# update-pr-review

Use this skill to turn human feedback on bot PR reviews into concise updates to
repo-local review companion skills.

This skill owns only the self-evolution logic: how to turn aggregated human
feedback into local review guidance. The GitHub Actions runner owns data
collection, write-surface validation, commits, pushes, and PR creation.

## Workflow

1. Read the aggregated feedback JSON provided by the runner.
2. Identify repeated human-feedback patterns or stable repo preferences.
3. Convert those patterns into concise repo-specific guidance.
4. Update only the matching local companion skill or skills.
5. Stop; the runner validates and publishes the result.

## Learn And Edit

Read the JSON and look for patterns worth adding to local review rules:

- humans clearly said an agent comment was wrong
- the finding was directionally right, but severity, scope, or line target was wrong
- the comment was not actionable
- reviewers repeatedly emphasized a repo-specific check
- human-only review threads reveal stable repo preferences
- a pattern belongs in the top-level summary instead of inline comments

Turn concrete feedback into repo-specific guidance:

1. Start from the specific human feedback.
2. Find repeated patterns or stable repo preferences.
3. Abstract the pattern into guidance that applies to future reviews.
4. Merge it into the most relevant existing section.
5. Keep the final wording concise.

Acceptable edits:

- add a bullet to an existing section
- add a small section when no existing section fits
- rewrite an existing rule to make it more accurate
- make no change when the evidence is too weak

Do not:

- paste raw JSON into skill files
- write a chronological summary of PR feedback
- add a rule for one reviewer's one-off preference
- weaken correctness, security, or data-loss checks from one disagreement
- override the core review contract

## Write Routing

Use each PR's `review_type`:

- `code` -> `.agents/skills/review-pr-local/SKILL.md`
- `spec` -> `.agents/skills/review-spec-local/SKILL.md`

Skip a file when that feedback type has no useful pattern.

## Boundaries

Allowed write surface:

- `.agents/skills/review-pr-local/`
- `.agents/skills/review-spec-local/`

Forbidden write surface:

- `.agents/skills/review-pr/SKILL.md`
- `.agents/skills/review-spec/SKILL.md`
- other core skills or product code

Local companion skills may specialize repo preferences, but must not change the
core review contract: output schema, severity labels, diff-line targeting,
snapshot rules, validation rules, or safety rules.

## Handoff

After editing, re-read the updated local skills and keep them concise. Do not
run Git commands, push branches, create PRs, or edit workflow files as part of
this skill. The runner must validate the write surface before publishing.
