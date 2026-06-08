---
name: security-review-spec
description: Audit a product or tech spec pull request diff for high-level security concerns (threat surface, authentication and authorization model, trust boundaries, sensitive data handling, secrets and key management, dependency posture, and abuse or misuse cases) and fold findings into the same review.json produced by the base spec review. Use as a supplement to `review-spec` whenever a spec PR is being reviewed.
---

# Security Review Spec Skill

Audit the current spec pull request for design-level security concerns and fold
any findings into the same `review.json` produced by `review-spec`.

## Required Contract

Read `.agents/contracts/review.md` and follow it exactly. This skill is a
supplement to `review-spec`; it must not create a separate report, change the
`review.json` schema, loosen diff-line targeting, post to GitHub, perform
code-level review, or regenerate snapshots.

## When To Apply

- Apply on spec PRs whenever `review-spec` is applied.
- Do not apply on code PRs handled by `review-pr`.
- Skip the skill when the changed spec content has no plausible security
  surface, such as purely editorial wording, typo fixes, or doc structure
  cleanup.
- Do not duplicate findings the base `review-spec` pass will already raise.

## Security Concerns

Evaluate changed spec content at the design-doc level. Focus on gaps or
ambiguities that would plausibly lead to an insecure implementation.

### Threat Surface And Trust Boundaries

- New external inputs, endpoints, webhooks, CLI surfaces, or file formats
  without clear reachability and trust assumptions.
- User-supplied or third-party content flowing into automation, prompts,
  commands, or storage without a validation or sanitization plan.
- Features that expand what unauthenticated or low-privilege actors can cause
  the system to do.
- Agent or LLM-driven flows where untrusted input can be interpreted as
  instructions without a mitigation.

### Authentication And Authorization

- New actors, roles, automation identities, or triggers without clear
  authentication and authorization rules.
- Informal enforcement language such as "only maintainers can trigger this"
  without saying how the workflow enforces it.
- Privilege escalation where a less-privileged actor can cause a more-privileged
  bot, workflow, or agent to act on their behalf.

### Sensitive Data, Secrets, And Privacy

- New data collection, storage, logging, or transmission without sensitivity,
  retention, or access-control expectations.
- Private repository contents, personal data, auth tokens, session identifiers,
  or customer data routed through logs, prompts, or third-party services without
  a redaction plan.
- New credentials, API keys, signing keys, or tokens without storage, access,
  rotation, and leak-response expectations.

### Abuse, Dependencies, Defaults, And Observability

- Externally triggerable automation without rate limiting, deduplication, retry,
  or cost-control expectations.
- Recursive or unbounded work caused by comments, webhooks, scheduled jobs, or
  poisoned inputs.
- New third-party services, registries, models, or binaries without trust or
  pinning assumptions.
- Unsafe or unspecified defaults where the safe choice is not obvious.
- Security-relevant operations without logging, log protection, or abuse
  detection expectations.

## Reporting

- Prefix every security finding's comment body with `[SECURITY]` after the
  severity label, for example `⚠️ [IMPORTANT] [SECURITY] Authentication model for new webhook is unspecified: ...`.
- Add a `## Security` subsection to the top-level review body only when there
  are security findings.
- Count security findings toward the same review summary and verdict. A critical
  design-level security gap should generally produce `REJECT`.
- Tie findings to changed spec lines when possible. Put broad or cross-document
  concerns in top-level `body`.

## Boundaries

- Do not perform code-level review.
- Do not run dynamic scans, fetch remote advisories, or call external security
  APIs.
- Do not treat a spec as insecure just because it does not enumerate every
  threat; focus on concerns likely to cause a missed mitigation.
