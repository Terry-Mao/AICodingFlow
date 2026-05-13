# AICodingFlow

AICodingFlow provides a small, opinionated Git workflow for Codex-based development. It packages reusable local Codex skills for branch creation, commits, pushes, pull requests, and an optional GitHub Actions workflow that runs offline AI pull request review from stable PR snapshots.

The project focuses on predictable repository hygiene:

- create issue-backed branches with consistent names
- produce atomic, reviewable commits from real diffs
- push branches without rewriting remote history by accident
- create or update pull requests without losing human-written PR context
- run AI PR review in GitHub Actions using pinned `pr_diff.txt` and `pr_description.txt` inputs

## Quick Start

Clone this repository and install the local skills:

```bash
git clone git@github.com:Terry-Mao/AICodingFlow.git
cd AICodingFlow

mkdir -p ~/.agents/skills
for skill in .agents/skills/*; do
  [ -d "$skill" ] || continue
  rsync -a "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

Preview the install before writing files:

```bash
for skill in .agents/skills/*; do
  [ -d "$skill" ] || continue
  rsync -ani "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

The installer updates only the skill directories present in this repository. It does not delete unrelated skills under `~/.agents/skills/`.

After installation, use the skills from Codex by naming them in your request:

```text
$git-branch #16
$git-commit
$git-push
$create-pr
```

## Modules

### Local Git Skills

Skills are installed into `~/.agents/skills/` and are intended to be used from Codex.

| Skill | Purpose |
| --- | --- |
| `git-branch` | Creates branches that follow repository naming rules, including issue-backed names such as `<type>/<short-desc>-<issueID>`. |
| `git-commit` | Builds clean commits from actual diffs, checks repo conventions, stages only intended files or hunks, and reports validation status. |
| `git-push` | Publishes committed branch work safely, sets upstream when needed, and avoids unsafe force pushes. |
| `create-pr` | Creates or updates GitHub pull requests after local diff review, base sync, validation, and issue linking. |
| `create-product-spec` | Wraps product spec writing for GitHub issues and writes `specs/issue-<issue-number>/product.md`. |
| `create-tech-spec` | Wraps tech spec writing for GitHub issues and writes `specs/issue-<issue-number>/tech.md`. |
| `review-pr` | Reviews a PR from pinned local snapshots and writes a validated `review.json` for GitHub Actions. |
| `review-pr-local` | Wraps `review-pr` with AICodingFlow-specific review guidance for this repository. |
| `review-spec` | Reviews spec-only PRs from pinned local snapshots and writes a validated `review.json` focused on document quality. |
| `review-spec-local` | Captures AICodingFlow-specific guidance for spec-only PR reviews. |
| `spec-driven-implementation` | Guides substantial feature work with pragmatic product and tech specs under `specs/`. |
| `write-product-spec` | Drafts behavior-oriented `product.md` specs for users, maintainers, contributors, and agents. |
| `write-tech-spec` | Drafts implementation-oriented `tech.md` specs grounded in the current codebase. |
| `implement-specs` | Implements approved product and tech specs while keeping them current with code changes. |
| `update-pr-review` | Aggregates human feedback on bot reviews and updates repo-local review companion skills. |

Reference files and validators live next to their skills:

```text
.agents/skills/git-branch/references/issue-id-examples.md
.agents/skills/git-commit/references/commit-examples.md
.agents/skills/review-pr-local/SKILL.md
.agents/skills/review-spec/SKILL.md
.agents/skills/review-spec-local/SKILL.md
.agents/skills/update-pr-review/scripts/aggregate_review_feedback.py
.agents/skills/review-pr/scripts/validate_review_json.py
```

### GitHub Workflow Files

The GitHub Actions workflow and helper scripts live in the repository root `.github/` directory:

```text
.github/workflows/review-pr.yml
.github/workflows/create-spec-from-issue.yml
.github/scripts/write_pr_description.py
.github/scripts/build_pr_diff.py
.github/scripts/post_pr_review.py
.github/scripts/prepare_issue_spec_context.py
.github/scripts/validate_spec_output.py
```

There is no separate `assets/.github/` template. Copy `.github/` directly into a target repository when enabling the PR review workflow there.

## GitHub Action: AI PR Review

The included workflow runs on pull request events, snapshots the PR description and diff, invokes Codex with the `review-pr-local` skill, validates the generated `review.json`, and posts the review back to GitHub.

### What It Does

1. Checks out the PR head commit.
2. Writes `pr_description.txt` from `GITHUB_EVENT_PATH`.
3. Converts the PR diff into `PR_DIFF_V1` as `pr_diff.txt`.
4. Runs `openai/codex-action@v1` with the `review-pr-local` skill.
5. Validates `review.json` with `.agents/skills/review-pr/scripts/validate_review_json.py`.
6. Posts body and inline comments with `.github/scripts/post_pr_review.py`.
7. Uploads `pr_description.txt`, `pr_diff.txt`, and `review.json` as artifacts.

The workflow intentionally reviews only non-draft pull requests from the same repository:

```yaml
if: github.event.pull_request.draft == false && github.event.pull_request.head.repo.full_name == github.repository
```

This avoids running write-permission review automation on forked PRs.

### Required Configuration

Configure these repository settings before enabling the workflow:

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Actions secret | Yes | API key used by `openai/codex-action@v1`. |
| `OPENAI_API_ENDPOINT` | Actions variable | Yes | Responses API endpoint. The workflow accepts either a base URL or a URL ending in `/responses`. |
| `GITHUB_TOKEN` | Built-in Actions token | Automatic | Used by `.github/scripts/post_pr_review.py` to create a PR review. |

The workflow declares the permissions it needs:

```yaml
permissions:
  contents: read
  pull-requests: write
```

Set the OpenAI values in GitHub:

1. Go to `Settings -> Secrets and variables -> Actions`.
2. Add secret `OPENAI_API_KEY`.
3. Add variable `OPENAI_API_ENDPOINT`.
4. Confirm Actions are enabled for the repository.

### Enable In Another Repository

Copy the workflow, scripts, and skills into the target repository:

```bash
rsync -a .github/ /path/to/target-repo/.github/
rsync -a .agents/ /path/to/target-repo/.agents/
```

Commit the copied files in the target repository and configure the required GitHub secret and variable.

## Development

Run the Python test suite:

```bash
python3 -m unittest discover -s tests
```

Useful files when changing the review workflow:

- `.github/scripts/build_pr_diff.py`: converts `git diff` output into `PR_DIFF_V1`
- `.github/scripts/post_pr_review.py`: posts validated review comments through the GitHub API
- `.agents/skills/review-pr/scripts/validate_review_json.py`: validates review output before posting
- `tests/`: unit tests for diff conversion, review posting, and validation behavior

## Contributing

Contributions are welcome through issues and pull requests.

Recommended flow:

1. Open or choose an issue.
2. Create an issue-backed branch with `git-branch`, for example `$git-branch #16`.
3. Keep changes focused and covered by tests when behavior changes.
4. Run `python3 -m unittest discover -s tests`.
5. Commit with `git-commit`.
6. Push with `git-push`.
7. Open or update the PR with `create-pr`.

Please keep skill instructions concise, operational, and safe. Avoid adding broad automation that stages unrelated files, rewrites history, deletes user data, or posts to external services without a clear workflow boundary.

## Reporting Bugs

Use GitHub Issues to report bugs or request improvements. Include:

- what you were trying to do
- the skill or workflow involved
- relevant command output or GitHub Actions logs
- expected behavior
- actual behavior
- repository context, such as branch name and whether the worktree was dirty

For PR review workflow bugs, attach the uploaded artifacts when possible:

```text
pr_description.txt
pr_diff.txt
review.json
```

These files make review output and line-number issues reproducible.

## GitHub Action: Create Spec From Issue

The `create-spec-from-issue.yml` workflow turns ready GitHub issues into spec
pull requests. It can be run manually with an issue number, or from issue events
when an issue has `ready-to-spec` and is assigned to the configured agent login.
It also supports comment-triggered runs on `ready-to-spec` issues when the
comment mentions that agent login.

Set repository variable `SPEC_AGENT_LOGIN` to the GitHub login that maintainers
will assign or mention, such as a dedicated machine user or installed app bot.
`github-actions[bot]` is only the workflow actor used for commits and API calls;
do not use it as the product trigger Bot unless it is actually assignable and
mentionable in the repository.

The workflow prepares stable issue context, runs Codex with the spec skills in
this order, validates the outputs, pushes `spec/issue-<N>`, and creates or
updates the spec PR:

1. `spec-driven-implementation`
2. `write-product-spec`
3. `create-product-spec`
4. `write-tech-spec`
5. `create-tech-spec`

Expected generated files:

```text
specs/issue-<N>/product.md
specs/issue-<N>/tech.md
pr-metadata.json
```

The generated `product.md` and `tech.md` should use the primary natural language
of the issue context, while keeping code identifiers and paths unchanged.

`pr-metadata.json` is used by the workflow to title and describe the PR. Its
`pr_title` must use conventional commit style, and its markdown `pr_summary`
must include `Refs #<N>`. Only the spec files are committed.

This workflow is spec-only. It must not implement the feature or modify
production code; implementation is handled by a separate workflow.

The generated `issue_context.json` includes issue number, title, body, labels,
assignees, comment count, triggering comment when present, default branch,
target branch, normalized spec paths, and coauthor directives.
The separate `issue_comments.txt` contains historical issue discussion; when a
comment triggers the run, that triggering comment is excluded from
`issue_comments.txt` and kept only in `issue_context.json.triggering_comment`.
