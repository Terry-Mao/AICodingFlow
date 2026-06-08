---
name: review-spec-local
description: Run the repository spec review workflow locally from the current branch using temporary-directory snapshots and the same review.json contract as CI.
---

# review-spec-local

Use this skill after local spec work and before pushing or creating a spec PR.
It prepares the same review inputs used by the GitHub review workflow, then
delegates review logic to `review-spec`.

## Workflow

1. From the repository root, prepare local review inputs. This prefers the
   GitHub PR associated with the current branch for `pr_description.txt`, then
   falls back to locally built PR metadata when the GitHub PR cannot be fetched.
   The `pr_diff.txt` snapshot is built from the local worktree diff. The command
   writes snapshots to a temporary directory and prints the selected review
   skill as `skill=<path>` plus exact file paths:
   ```bash
   python3 .github/scripts/prepare_local_review_inputs.py
   ```
2. Read the `skill` path printed by the command.
3. Follow the selected skill exactly. It will apply any referenced local
   companion guidance when present.
4. Use only the printed snapshot paths as review inputs:
   - `pr_description_path`
   - `pr_diff_path`
5. Inspect repository files from the current repository root when the review
   skill needs source context.
6. Write the review output only to the printed `review_path`.
7. Validate the review output:
   ```bash
   python3 .github/scripts/validate_review_json.py <pr_diff_path> <review_path>
   ```
8. Validate that the review phase did not mutate repository files:
   ```bash
   python3 .github/scripts/validate_local_review_result.py \
     --baseline-status <baseline_status_path>
   ```

## Safety Rules

- After input preparation, do not run `git add`, `git commit`, `git push`,
  `gh`, or GitHub API commands.
- Do not post comments or mutate GitHub state.
- Do not modify source, workflow, tests, specs, or skill files.
- If review discovers issues, report them through `review.json`; do not fix
  specs during this skill.
