---
name: write-product-spec
description: Write a product spec for a significant user-facing feature in this repository, focused on detailed behavior and validation. Use when the user asks for a product spec, desired behavior doc, or PRD, wants to define feature behavior before implementation, or when the feature is substantial or behaviorally ambiguous enough that a written spec would improve implementation or review.
---

# write-product-spec

Write a product spec for a significant feature in this repository.

## Overview

This skill is the local shared product-spec workflow for this repository. Local wrappers and workflows depend on it directly as the canonical product-spec contract.

The product spec should make the desired behavior unambiguous enough that an agent can implement it correctly and avoid regressions while making changes. Focus on product behavior, UX, invariants, and validation rather than implementation details.

Write specs into source control under a repository-appropriate path within `specs/`.

If a repo-specific wrapper skill or explicit prompt provides an exact output path, follow that path. Otherwise prefer a clear structure such as:

- `specs/<topic>/product.md`

## Before writing

Gather the minimum context needed to write the spec:

- the feature summary
- target users or workflow
- key user-facing behaviors and constraints
- known edge cases
- expected verification plan
- any tracker or issue identifier when the surrounding workflow depends on one

When the request leaves important details unspecified, use `ask_user_question` to gather the missing context instead of guessing.

If the feature includes UI or interaction changes, ask whether there is a Figma mock.

### Figma guidance

If a Figma mock exists, include a link to it in the spec.

If the user does not provide one and the session is interactive, ask whether a mock exists. Otherwise, note the absence and continue. Do not silently omit design context.

For example, include a short note such as:

- `Figma: <link>`
- `Figma: none provided`

No Figma mock is acceptable, but the absence should be explicit.

## What to write

Use the following structure:

### 1. Summary

Describe the feature in a few sentences and state the desired outcome.

### 2. Problem

Explain what user or product problem is being solved.

### 3. Goals

List the outcomes this change must achieve.

### 4. Non-goals

List adjacent ideas or follow-ups that are explicitly out of scope.

### 5. Figma / design references

Link the Figma mock if it exists, or explicitly note that none was provided.

### 6. User experience

Describe expected behavior in concrete, exhaustive, testable terms. Aim for a complete textual description of the user-visible behavior that reviewers can verify through tests, screenshots, videos, and code review. Be explicit about:

- default behavior
- state transitions
- edge cases
- empty states
- error states
- keyboard or interaction expectations when relevant

When useful, write this section as a list of invariants or behavior rules rather than broad prose. Prefer too much relevant detail over vague summary language.

### 7. Success criteria

Define in high detail what will be true if the feature works correctly. Each criterion should map to observable user behavior and be specific enough that an implementer or reviewer can verify it with tests and by inspecting the code. Prefer concrete, observable outcomes over vague quality claims, and include important states, transitions, and edge cases when they matter to correctness.

### 8. Validation

Describe how the behavior should be verified. Prefer checks that can map cleanly to tests, videos, screenshots, or manual validation steps.

### 9. Open questions

Call out unresolved product decisions rather than burying them in the narrative.

## Writing guidance

- Prefer concrete behavior over aspirational wording.
- Write for the implementer and reviewer, not for marketing.
- Make the spec precise enough that an agent can follow it.
- Capture invariants that must not regress.
- Include edge cases that are easy to miss in implementation.
- Avoid implementation details unless they are unavoidable for understanding the UX.

## When to avoid this skill

Skip the product spec when the change is small enough that the overhead outweighs the value. As a rough guideline, specs are most useful for significant features rather than small edits.

## Keep the spec current

If the implementation changes the intended product behavior, update the checked-in product spec so it still matches what ships.

Approved specs may be implemented in the same PR as the code. As implementation evolves, keep updates to the product spec, tech spec, and code in that same PR when practical.

Update the product spec when any of these change:

- user-facing behavior
- UX details
- success criteria
- validation expectations

For large features, the implementer may optionally keep a `DECISIONS.md` file that summarizes concrete product and technical decisions made during spec and implementation work. This is optional and should be offered when it would help keep the work coherent.

## Related Skills

- `implement-specs`
- `write-tech-spec`
- `spec-driven-implementation`
