---
name: create-tech-spec
description: Create a technical spec from a GitHub issue in this repository by applying the local shared `write-tech-spec` workflow with issue context and output paths. Use when an issue should be turned into a tech spec artifact stored under `specs/issue-<issue-number>/tech.md` and the agent should prepare file changes only, without creating commits or pull requests itself.
---

# create-tech-spec

Create a tech spec from a GitHub issue for this repository.

## Overview

This skill is a wrapper around the local shared tech-spec workflow:

- `.agents/skills/write-tech-spec/SKILL.md`

Use that shared local skill as the base behavior and structure unless this wrapper overrides it. Keep the same emphasis on grounding the plan in current code, documenting relevant files and data flow, explaining tradeoffs, and defining validation.

The differences are:

- the primary input is a GitHub issue, not a Linear issue
- the output path is `specs/issue-<issue-number>/tech.md`
- `issue_context.json` contains the issue details, triggering comment, output paths, target branch, and workflow metadata
- `issue_comments.txt` contains prior issue discussion, excluding the explicit triggering comment
- a workflow may also request a structured PR metadata file in `pr-metadata.json`
- do not create or edit Linear issues as part of this workflow
- the spec language should follow the primary natural language of the GitHub issue context

## Inputs

Expect issue details in `issue_context.json`, including the issue number, title, description, labels, assignees, triggering comment when present, exact `product_spec` path, and exact `tech_spec` path.

When available, the product spec at the `product_spec` path from `issue_context.json` should be treated as the primary input for understanding the intended behavior. The tech spec translates that product intent into an implementation approach.

Write the tech spec in the primary natural language of the issue title, issue body, explicit triggering comment, and product spec. For primarily Chinese issues, write Chinese. For primarily English issues, write English. Keep code identifiers, file paths, labels, branch names, and API names unchanged.

## Workflow

1. Start from the local shared `write-tech-spec` guidance and follow its structure and writing standards unless this wrapper says otherwise.
2. Read `issue_context.json` carefully. Read the product spec from the exact `product_spec` path first to understand the intended behavior. If `issue_comments.txt` exists, review it for clarifications, prior decisions, and design nuance that should influence the tech plan.
3. Inspect the repository to understand the current implementation and the likely scope of the requested work before writing the spec. Do not guess about current architecture when the code can be inspected directly.
4. Create or update the exact `tech_spec` path from `issue_context.json`.
5. Use the shared skill's structure as the baseline, adapted to this repository and issue format. At minimum, cover:
   - problem
   - relevant code
   - current state
   - proposed changes
   - end-to-end flow when useful
   - risks and mitigations
   - testing and validation
   - follow-ups or open technical questions
6. Keep the tech spec concise, actionable, and grounded in actual code paths and ownership boundaries in this repository.
7. Do not implement the feature or modify production code as part of this task. Limit changes to the tech spec artifact and any minimal repository metadata needed to support it. Treat temporary context files such as `issue_context.json` and `issue_comments.txt` as scratch input only and do not commit them.
8. Do not include issue number references (e.g. `(#N)`, `Refs #N`) in commit messages. The issue is already linked in the PR.
9. If the prompt asks for it, write `pr-metadata.json` at the repository root containing a JSON object with the fields `branch_name`, `pr_title`, and `pr_summary`. The `pr_summary` should summarize the resulting spec changes, validation, and any reviewer-relevant assumptions or open questions. For spec-only PRs, include a non-closing reference to the source issue such as `Refs #<issue-number>` rather than closing keywords like `Closes` or `Fixes`.
10. Default behavior: do not stage files, create commits, push branches, open pull requests, or use the GitHub CLI.
11. In your final response, provide a brief summary of the tech spec and call out any assumptions or open questions so the workflow can reuse that summary when creating the PR.

## Output expectations

- Leave the repository with the new or updated tech spec file ready to be committed by the workflow.
- When requested by the prompt, leave a ready-to-use `pr-metadata.json` with `branch_name`, `pr_title`, and `pr_summary`.
- If the issue is underspecified, still produce the best possible tech spec and clearly capture assumptions or open questions in the spec file and final response.
