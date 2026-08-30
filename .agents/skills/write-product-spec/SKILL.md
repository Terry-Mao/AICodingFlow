---
name: write-product-spec
description: Write a behavior-focused product spec for a significant or ambiguous feature in this repository.
---

# write-product-spec

Write the product contract an implementer and reviewer can use to agree on
observable behavior. This is a local shared skill; wrappers may provide exact
inputs and output paths that take precedence.

## Decide and prepare

Use it when behavior, scope, risk, or user impact is substantial enough that a
checked-in spec will reduce ambiguity. Skip it for small fixes, straightforward
refactors, and narrow low-risk changes.

Specs normally live under `specs/`. Without an explicit wrapper or prompt path,
use `specs/<topic>/product.md`; preserve this repository's lowercase filenames
and issue-backed layout. Do not create an issue or other tracker item unless
the user explicitly asks.

Gather only the feature summary, affected users/consumers, desired behavior,
edge cases, validation needs, and relevant issue context. Here, “user” may be
an end user, maintainer, operator, API caller, contributor, or agent consuming
the designed surface. Ask about missing product decisions instead of guessing.

For UI or interaction work, ask whether a Figma mock exists before drafting
behavior. Include its link, or explicitly write `Figma: none provided`; skip
this for non-visual features.

## Write the spec

Keep the spec implementation-light. Required sections are:

1. **Summary** — the feature and desired outcome in 1–3 sentences.
2. **Problem** — the user or product problem when it is not already obvious.
3. **Goals** — observable outcomes the change must achieve.
4. **Non-goals** — adjacent work that is intentionally out of scope.
5. **Figma / design references** — only for visual work; include the link or
   explicit absence.
6. **User experience** — the main contract. Prefer numbered, testable behavior
   invariants covering defaults, inputs, state transitions, loading/empty/error
   states, cancellation, stale or missing data, permissions, races, and
   keyboard/accessibility expectations when relevant.
7. **Success criteria** — concrete outcomes a reviewer can observe; do not
   duplicate the behavior section with generic quality claims.
8. **Validation** — how the behavior will be checked with tests or manual
   evidence. Keep implementation-specific test design in the tech spec too.
9. **Open questions** — unresolved product decisions, preferably next to the
   behavior they affect.

The wrapper may require all sections above even when a standalone spec could
omit an empty optional section. Do not add implementation details, file plans,
or architecture here; those belong in `write-tech-spec`.

## Right-size and maintain

Keep framing thin and spend detail on behavior. A small feature is often about
30–60 lines, a medium feature about 80–150 lines, and a complex feature may be
longer when its edge cases earn the space. Length is a heuristic, not a target.

When implementation changes user-facing behavior, update the checked-in
`product.md` in the same change when practical. An optional `DECISIONS.md` can
record major product decisions for large features, but is not required.

Related skills: `write-tech-spec`, `spec-driven-implementation`, and
`implement-specs`.
