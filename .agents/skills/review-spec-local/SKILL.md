---
name: review-spec-local
description: Run the repository spec review workflow locally from the current branch using the same root-level snapshots and review.json contract as CI.
---

# review-spec-local

Use this skill after local spec work and before pushing or creating a spec PR.
It prepares the same review inputs used by the GitHub review workflow, then
delegates review logic to `review-spec-repo`.

## Workflow

1. From the repository root, prepare local review inputs:
   ```bash
   python3 .github/scripts/prepare_local_review_inputs.py \
     --expected-skill .agents/skills/review-spec-repo/SKILL.md
   ```
2. Read `.agents/skills/review-spec-repo/SKILL.md`.
3. Follow `review-spec-repo` exactly. It will read the core `review-spec` skill.
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
