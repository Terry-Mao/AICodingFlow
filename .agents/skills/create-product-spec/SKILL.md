---
name: create-product-spec
description: Create a product spec from a GitHub issue in this repository by applying the local shared `write-product-spec` workflow with issue context and output paths. Use when an issue should be turned into a product spec artifact stored under `specs/issue-<issue-number>/product.md` and the agent should prepare file changes only, without creating commits or pull requests itself.
---

# create-product-spec

Create a product spec from a GitHub issue for this repository.

## Overview

This skill is a wrapper around the local shared product-spec workflow:

- `.agents/skills/write-product-spec/SKILL.md`

Use that shared local skill as the base behavior and structure unless this wrapper overrides it. Keep the same emphasis on precise user-facing behavior, invariants, edge cases, validation, and open questions.

The differences are:

- the primary input is a GitHub issue, not a Linear issue
- the output path is `specs/issue-<issue-number>/product.md`
- `issue_context.json` contains the issue details, triggering comment, output paths, target branch, and workflow metadata
- `issue_comments.txt` contains prior issue discussion, excluding the explicit triggering comment
- a workflow may also request a structured PR metadata file in `pr-metadata.json`
- do not create or edit Linear issues as part of this workflow
- the spec language should follow the primary natural language of the GitHub issue context

## Inputs

Expect issue details in `issue_context.json`, including the issue number, title, description, labels, assignees, triggering comment when present, and exact `product_spec` path.

Use `issue_comments.txt` as prior discussion context when present. Treat comments as additional context, not as a silent override of the issue body. Resolved decisions from comments can refine the spec; unresolved disagreements should remain explicit open questions.

Write the product spec in the primary natural language of the issue title, issue body, and explicit triggering comment. For primarily Chinese issues, write Chinese. For primarily English issues, write English. Keep code identifiers, file paths, labels, branch names, and API names unchanged.

## Workflow

1. Start from the local shared `write-product-spec` guidance and follow its structure and writing standards unless this wrapper says otherwise.
2. Read `issue_context.json` carefully. If `issue_comments.txt` exists, review it for clarifications, prior decisions, and issue-comment nuance that should influence the spec.
3. Inspect the repository enough to understand the current user workflow and likely scope before writing the spec.
4. Create or update the exact `product_spec` path from `issue_context.json`.
5. Keep the product spec focused on intended behavior and user-facing requirements. Use the shared skill's sections as the baseline, adapted to this repository and issue format. At minimum, cover:
   - summary
   - problem
   - goals
   - non-goals or scope boundaries
   - concrete user experience and behavior requirements
   - success criteria
   - validation
   - open product questions
6. If design context such as a Figma link is present in the issue description or comments, include it. If no design context exists, make that absence explicit rather than silently omitting it.
7. Do not include implementation details, file-level changes, or technical design. Those belong in the tech spec.
8. Do not implement the feature or modify production code as part of this task. Limit changes to the product spec artifact. Treat temporary context files such as `issue_context.json` and `issue_comments.txt` as scratch input only and do not commit them.
9. Do not include issue number references (e.g. `(#N)`, `Refs #N`) in commit messages. The issue is already linked in the PR.
10. If the prompt asks for it, write `pr-metadata.json` at the repository root containing a JSON object with the fields `branch_name`, `pr_title`, and `pr_summary`. The `pr_summary` should summarize the product and technical planning clearly enough that reviewers can use it directly as the PR body. For spec-only PRs, include a non-closing reference to the source issue such as `Refs #<issue-number>` rather than closing keywords like `Closes` or `Fixes`.
11. Default behavior: do not stage files, create commits, push branches, open pull requests, or use the GitHub CLI.
12. In your final response, provide a brief summary of the product spec and call out any assumptions or open questions so the workflow can reuse that summary when creating the PR.

## Output expectations

- Leave the repository with the new or updated product spec file ready to be committed by the workflow.
- When requested by the prompt, leave a ready-to-use `pr-metadata.json` with `branch_name`, `pr_title`, and `pr_summary`.
- If the issue is underspecified, still produce the best possible product spec and clearly capture assumptions or open questions in the spec file and final response.
