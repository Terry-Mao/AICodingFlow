---
name: bootstrap-issue-config
description: Bootstrap the issue triage configuration for a repository by analyzing existing issues, labels, and contributors to generate `.github/issue-triage/config.json` and `.github/CODEOWNERS`. Use when setting up triage automation on a new or existing repository for the first time.
---

# Bootstrap issue triage configuration

Analyze the target repository and generate (or update) the issue triage configuration files used by the `triage-new-issues` workflow.

## Outputs

This skill produces two files:

1. **`.github/issue-triage/config.json`** — label definitions used during triage.
2. **`.github/CODEOWNERS`** — CODEOWNERS-style ownership mappings from path patterns to GitHub usernames.

## Workflow

### 1. Discover existing labels

- Use `gh label list --repo <owner>/<repo> --limit 200 --json name,color,description` to fetch all labels currently defined on the repository.
- Classify each label into one of three categories:
  - **area** labels — identify a component or subsystem (e.g. `area:api`, `area:docs`).
  - **feature** labels — identify a capability or request type (e.g. `enhancement`, `bug`, `documentation`).
  - **status** labels — identify workflow state (e.g. `triaged`, `needs-info`, `wontfix`).
- If the repository has very few or no labels, seed the config with sensible defaults:
  - `triaged` (status), `bug` (feature), `enhancement` (feature), `documentation` (feature), `needs-info` (status), `duplicate` (status)
  - `repro:high`, `repro:medium`, `repro:low`, `repro:unknown` (status)

### 2. Analyze recent issues

- Use `gh issue list --repo <owner>/<repo> --state all --limit 100 --json number,title,labels,createdAt` to fetch recent issues.
- If issues use labels that are not yet captured, add them to the appropriate category.
- Look at `.github/ISSUE_TEMPLATE/` for template files — template names and labels referenced in templates can inform label discovery.

### 3. Generate or update `config.json`

- Read any existing `.github/issue-triage/config.json`.
- Merge newly discovered labels into the existing `labels` object. Do **not** remove labels that already exist in the config — only add or update.
- The config must contain **only** the `labels` key. Do **not** include `stakeholders` or `default_experts`.
- `labels` must be a flat object keyed by the exact GitHub label name, including prefixes such as `area:workflow` or `repro:high`. Do not nest labels by category.
- Each label entry must have `color` (6-character hex without `#`) and `description` (one-sentence summary):
  ```json
  {
    "labels": {
      "triaged": {
        "color": "0E8A16",
        "description": "Initial triage has been completed for this issue"
      },
      "area:workflow": {
        "color": "7057FF",
        "description": "GitHub workflows, Python automation, or integration"
      }
    }
  }
  ```
- Write the result to `.github/issue-triage/config.json`.
- Validate with `jq . .github/issue-triage/config.json`.

### 4. Generate or update `.github/CODEOWNERS`

- Inspect `CODEOWNERS` if it exists for initial ownership hints.
- Use `git log --format='%aN <%aE>' --since='6 months ago' -- <path>` and `gh api` to identify recent contributors to major directories.
- Read any existing `.github/CODEOWNERS` file and merge new entries rather than overwriting.
- Write the file using CODEOWNERS conventions:
  ```
  # Syntax follows CODEOWNERS conventions: later rules take precedence.
  # GitHub may request code owner review when branch protection requires it.

  # --- Section comment ---
  /path/pattern/ @owner1 @owner2
  ```
- Each line maps a path glob to one or more `@username` owners.

### 5. Create missing labels

- For every label in the final `config.json` that does not already exist on the repository, create it:
  ```
  gh label create "<name>" --color "<color>" --description "<description>" --repo <owner>/<repo>
  ```
- Skip labels that already exist (the `gh label create` command will error on duplicates — ignore those errors).

### 6. Note repo-local companion skills (do not scaffold)

The reusable agent roles that support a repo-specific companion are:

- `.agents/skills/review-pr-repo/SKILL.md`
- `.agents/skills/review-spec-repo/SKILL.md`
- `.agents/skills/triage-issue-repo/SKILL.md`
- `.agents/skills/dedupe-issue-repo/SKILL.md`

Do **not** create these files during bootstrap. The prompt-construction layer treats a missing companion file and a body-only frontmatter stub the same way, so there is no value in materializing an empty file during bootstrap. Each file gets created on-demand by the matching `update-<agent>` self-improvement loop (or by a maintainer) the first time there is evidence-backed content to add. Bootstrap only needs to ensure the directory convention is documented; the files themselves stay absent until a real rule lands.

If a companion file already exists in the repo, leave it untouched; bootstrap is additive.

### 7. Validate and summarize

- Re-validate `config.json` with `jq`.
- Print a short summary of:
  - How many labels were discovered vs. newly created.
  - How many codeowner entries were written.
  - Which repo-local companion skills are already present in the repo (if any).
  - Any warnings (e.g. no issues found, no CODEOWNERS file).

## Idempotency

This skill is designed to be run multiple times safely. Re-running will:
- Merge new labels into the existing config without removing old ones.
- Merge new codeowner entries without duplicating existing lines.
- Skip label creation for labels that already exist on the repository.

## Assumptions

- The `gh` CLI is authenticated and has access to the target repository.
- The skill is run from the repository root.
- The target repository is the current working directory unless the prompt specifies otherwise.
