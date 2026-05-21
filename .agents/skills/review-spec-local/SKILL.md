---
name: review-spec-local
description: Run the repository spec review workflow locally from the current branch using the same root-level snapshots and review.json contract as CI.
---

# review-spec-local

Use this skill after local spec work and before pushing or creating a spec PR.
It prepares the same review inputs used by the GitHub review workflow, then
delegates review logic to `review-spec`.

## Workflow

1. From the repository root, prepare local review inputs. This prefers the
   GitHub PR associated with the current branch for `pr_description.txt`, then
   falls back to locally built PR metadata when the GitHub PR cannot be fetched.
   The `pr_diff.txt` snapshot is built from the local worktree diff, and the
   command prints the selected review skill as `skill=<path>`:
   ```bash
   python3 .github/scripts/prepare_local_review_inputs.py
   ```
2. Read the skill path printed by the command.
3. Follow the selected skill exactly. It will apply any referenced local
   companion guidance when present.
4. Use only these root-level snapshots as review inputs:
   - `pr_description.txt`
   - `pr_diff.txt`
5. Inspect repository files from the current repository root when the review
   skill needs source context.
6. Write only `review.json` in the repository root.
7. Validate the review output:
   ```bash
   python3 .github/scripts/validate_review_json.py pr_diff.txt review.json
   ```
8. Validate that the review phase did not mutate repository files:
   ```bash
   python3 .github/scripts/validate_local_review_result.py \
     --baseline-status .local_review_baseline.status
   ```

## Safety Rules

- After input preparation, do not run `git add`, `git commit`, `git push`,
  `gh`, or GitHub API commands.
- Do not post comments or mutate GitHub state.
- Do not modify source, workflow, tests, specs, or skill files.
- If review discovers issues, report them through `review.json`; do not fix
  specs during this skill.
