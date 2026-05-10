---
name: review-pr
description: Review a GitHub pull request from pinned `pr_diff.txt` and `pr_description.txt` snapshots, then write and validate `review.json`. Use when a CI job or bot needs offline PR review comments without posting to GitHub.
---

# review-pr

Review one PR from two existing snapshot files:

- `pr_description.txt`: PR title, body, and metadata.
- `pr_diff.txt`: line-annotated PR diff.

Do not run `gh`, post comments, or regenerate the snapshots during review. The only output artifact is `review.json`.

## Snapshot Files

Treat `pr_description.txt` and `pr_diff.txt` as the source of truth, even if the PR changes later. This keeps review content, line numbers, base SHA, and head SHA consistent.

For GitHub Actions setup, copy the repository root `.github/` template into the target project. Its scripts generate the two snapshot files before this skill runs.

`pr_diff.txt` uses `PR_DIFF_V1`:

```text
# PR_DIFF_V1
FILE path/to/file.py
HUNK @@ -10,7 +10,8 @@ optional heading
BOTH  10 | unchanged context
LEFT  11 | removed line
RIGHT 11 | added or modified line
RIGHT 12 | added line
END_FILE
```

Inline comments may target only `LEFT` or `RIGHT` lines present in `pr_diff.txt`; never target `BOTH` context lines.

## Review Scope

Prioritize concrete findings:

- correctness defects
- security risks
- exception and error handling gaps
- performance risks
- maintainability issues with clear impact
- documentation changes that disagree with code, examples, defaults, or behavior
- test changes that miss important assertions, over-mock behavior, or skip risky paths

Ignore pure style unless you can provide an exact GitHub `suggestion`. Put issues that cannot be attached to changed lines, such as missing tests or docs, in top-level `body`.

## Inline Comment Rules

Start every inline comment body with exactly one label:

- `🚨 [CRITICAL]`: bug, security issue, crash, data loss
- `⚠️ [IMPORTANT]`: logic issue, boundary case, missing exception handling
- `💡 [SUGGESTION]`: optimization or better implementation
- `🧹 [NIT]`: style cleanup; must include a `suggestion` block

Keep comments concise and actionable. Comment ranges must be 10 lines or fewer.

Use suggestion blocks only for exact replacements on `RIGHT` lines:

````markdown
```suggestion
replacement code
```
````

Do not use suggestions on `LEFT` lines. Omit `🧹 [NIT]` findings when no exact suggestion is possible.

## Output

Write `review.json` with exactly this shape:

```json
{
  "body": "Top-level review summary or issues that cannot be attached inline.",
  "comments": [
    {
      "path": "repo/relative/file.ext",
      "side": "RIGHT",
      "line": 42,
      "body": "⚠️ [IMPORTANT] concise finding..."
    }
  ]
}
```

For ranges, add `start_line`:

```json
{
  "path": "repo/relative/file.ext",
  "side": "RIGHT",
  "start_line": 40,
  "line": 42,
  "body": "💡 [SUGGESTION] concise finding...\n```suggestion\nreplacement\n```"
}
```

Constraints:

- `body` is a string; use `""` when empty.
- `comments` is an array; use `[]` when there are no inline findings.
- Each comment has `path`, `side`, `line`, and `body`.
- `side` is `LEFT` or `RIGHT`.
- Inline targets must match changed `path/side/line` entries from `pr_diff.txt`.
- If `start_line` is present, the full range must be changed lines on the same `path` and `side`.
- Do not wrap the whole JSON in markdown fences.

## Workflow

1. Read `pr_description.txt`.
2. Parse `pr_diff.txt` and build the allowed changed-line targets.
3. Inspect relevant repository files only when needed to understand changed code.
4. Write `review.json`.
5. Run `python3 skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`.
6. Fix `review.json` until validation passes.
7. Finish with only the validated `review.json` content.
