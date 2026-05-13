---
name: write-tech-spec
description: Write a tech spec for a significant feature in this repository after researching the current codebase and implementation constraints. Use when the user asks for a technical spec, implementation plan, or architecture doc tied to a product spec.
---

# write-tech-spec

Write a tech spec for a significant feature in this repository.

## Overview

This skill is the local shared tech-spec workflow for this repository. Local wrappers and workflows depend on it directly as the canonical tech-spec contract.

The tech spec should translate product intent into an implementation plan that fits the existing codebase, documents architectural choices, and makes the work easier for agents to execute and reviewers to evaluate.

Write specs into source control under a repository-appropriate path within `specs/`.

If a repo-specific wrapper skill or explicit prompt provides an exact output path, follow that path. Otherwise prefer a clear structure such as:

- `specs/<topic>/tech.md`

## When to use

Use this skill when:

- the feature is substantial
- the implementation spans multiple modules or layers
- there are meaningful architectural decisions or tradeoffs
- extensibility matters
- reviewers will benefit from understanding the plan before or alongside the code

For pure UI changes, a tech spec may be unnecessary. Be pragmatic.

## Prerequisites

Prefer to have a product spec first so the technical plan is anchored to agreed behavior.

If the implementation is still too uncertain, it can be better to build an end-to-end prototype first and then write the tech spec from what was learned. Do not force a speculative tech spec when the prototype is the fastest way to reduce ambiguity.

## Research before writing

Before drafting the tech spec:

1. Read the relevant product spec if it exists.
2. Inspect existing patterns in the codebase.
3. Identify the main files, types, data flow, and ownership boundaries involved.
4. Understand the current behavior and where it falls short.
5. Note dependencies, rollout constraints, risks, and likely validation strategy.

Do not guess about current architecture when the code can be inspected directly.

## What to write

Use the following structure:

### 1. Problem

State the technical problem being solved and how it relates to the product behavior.

### 2. Relevant code

Point to the most relevant files, types, and entry points so the implementation can start from real code rather than a blank page.

For example:

- `src/module.py:42` — entry point for the user flow
- `src/module.py (120-220)` — state and event handling that will likely change
- `src/components/button.tsx:10` — existing component pattern to follow

### 3. Current state

Describe how the system works today and what limitations matter for this feature.

### 4. Proposed changes

Lay out the implementation plan. Be explicit about:

- which modules or components change
- new types, APIs, or state that will be introduced
- data flow and event flow
- ownership boundaries
- how this design follows existing patterns in the repo

### 5. End-to-end flow

Explain the path through the system for the main user interaction or system behavior.

### 6. Risks and mitigations

Call out likely failure modes, regressions, migration concerns, or rollout hazards.

### 7. Testing and validation

List the tests and other verification needed to show the implementation matches the intended behavior.

### 8. Follow-ups

Note deferred cleanup, extensions, or future work that should not block the current implementation.

## Writing guidance

- Ground the plan in actual codebase structure and patterns.
- Prefer concrete implementation guidance over generic architecture language.
- Explain why the proposed design fits this repo.
- Call out tradeoffs when there is more than one reasonable path.
- Keep the document concise, but specific enough that an agent can implement from it.

## Keep the spec current

If implementation diverges from the planned architecture, update the checked-in tech spec so it still matches reality.

Approved specs may be implemented in the same PR as the code. As implementation evolves, keep updates to the product spec, tech spec, and code in that same PR when practical.

Update the tech spec when any of these change:

- module boundaries or ownership
- implementation sequencing
- risks or mitigations
- validation strategy
- rollout or dependency assumptions

For large features, the implementer may optionally keep a `DECISIONS.md` file that summarizes concrete product and technical decisions made during spec and implementation work. This is optional and should be offered when it would help future agents or reviewers understand how the design evolved.

## Related Skills

- `implement-specs`
- `write-product-spec`
- `spec-driven-implementation`
