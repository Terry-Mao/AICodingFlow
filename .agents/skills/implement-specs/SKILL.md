---
name: implement-specs
description: Implement approved product.md and tech.md specs while keeping those specs current. Use after spec-driven-implementation has produced or identified approved specs for a feature.
---

# implement-specs

Implement approved specs and keep them aligned with the code that will ship.

This is a placeholder skill for the spec-driven workflow. Keep it conservative
until the full workflow is developed.

## Scope

Before coding, read the relevant `product.md` and `tech.md` files. If only a
product spec exists, implement directly from that spec only when the work is
small enough that a tech spec is unnecessary.

During implementation:

- preserve the behavior and acceptance criteria from `product.md`
- follow the implementation plan from `tech.md` when present
- update `product.md` if externally observable behavior changes
- update `tech.md` if architecture, risks, affected files, or validation change
- verify the final behavior against the specs

Do not treat stale specs as authoritative. Update them in the same change when
the implementation intentionally diverges.
