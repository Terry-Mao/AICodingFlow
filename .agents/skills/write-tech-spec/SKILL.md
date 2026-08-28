---
name: write-tech-spec
description: Write a code-grounded technical spec for a substantial or ambiguous feature in this repository.
---

# write-tech-spec

Translate approved product intent into an implementation plan that fits the
existing codebase. This is a local shared skill; wrappers may provide exact
inputs and output paths that take precedence.

## Decide and research

Use it when work spans modules, has architectural tradeoffs, needs a migration
or rollout plan, or benefits from review before implementation. Skip it for
straightforward fixes, small refactors, and narrow UI changes with no technical
ambiguity. Prefer a product spec first; an end-to-end prototype can be a better
precedent when the implementation is still uncertain.

Before drafting, read the product spec when present and inspect the actual
repository. Identify current behavior, relevant files/types/entry points, data
or control flow, ownership boundaries, dependencies, risks, and validation
constraints. Do not infer architecture that can be read from code.

When a code reference matters, pin it to the inspected commit SHA and include a
repo-relative path with line numbers. Add a GitHub `blob/<sha>/...#Lx-Ly` link
when the repository has an accessible remote; otherwise keep the local
reference. Reference the product spec for behavior rather than restating it.

## Write the spec

Use the following core sections, keeping each only as detailed as the decision
requires:

1. **Problem** — the technical problem and its product relationship.
2. **Relevant code** — files, symbols, entry points, and current ownership.
3. **Current state** — how the system works and limitations that matter.
4. **Proposed changes** — affected modules, types/APIs/state, data flow,
   ownership boundaries, sequencing, and tradeoffs.
5. **Testing and validation** — map tests, manual checks, screenshots/videos,
   or other evidence to the product behavior and its numbered invariants.

Add these sections when they add signal:

- **End-to-end flow** — when tracing the main path clarifies the change list.
- **Risks and mitigations** — when there are real regression, migration,
  rollout, or compatibility hazards.
- **Follow-ups** — when there is deferred technical debt or an open technical
  question.

For small changes, combine the problem, current state, and relevant code into a
short context section when the wrapper permits it. Omit empty optional sections;
do not pad the document with generic architecture prose. Evaluate parallel
work only when the surrounding workflow explicitly allows delegation and it
materially reduces time or isolates ownership; otherwise omit it.

## Right-size and maintain

A single-file change may not need a tech spec; a multi-module feature is often
about 80–150 lines; larger documents are justified by real cross-cutting risk.
If implementation diverges from the plan, update `tech.md` in the same change
when practical. An optional `DECISIONS.md` can capture major technical choices
for large features, but is not required.

Related skills: `write-product-spec`, `spec-driven-implementation`, and
`implement-specs`.
