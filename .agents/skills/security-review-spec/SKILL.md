---
name: security-review-spec
description: Audit a product or tech spec pull request diff for high-level security concerns (threat surface, authentication and authorization model, trust boundaries, sensitive data handling, secrets and key management, dependency posture, and abuse or misuse cases) and fold findings into the same review.json produced by the base spec review. Use as a supplement to `review-spec` whenever a spec PR is being reviewed.
---

# Security Review Spec Skill

Audit the current spec pull request for security concerns at the design-doc level and fold any findings into the same `review.json` produced by the base `review-spec` skill.

## Goal

Provide a focused security pass on top of the general spec review. This is a supplement to `review-spec`, not a separate output. Findings must be merged into the single combined `review.json` so reviewers receive one cohesive review.

The focus here is high-level design concerns that a security-minded reader would raise on a product or tech spec, not line-by-line code issues. Flag gaps, ambiguities, or design choices that would plausibly lead to an insecure implementation if built as described.

## Context

- The working directory is the PR branch checkout.
- The workflow usually provides an annotated diff in `pr_diff.txt`.
- The workflow usually provides the PR description in `pr_description.txt`.
- Spec PRs typically only modify files under `specs/`.
- Focus on the spec files and sections changed by this PR.
- Default behavior: do not post comments or reviews to GitHub directly.

## When to apply this skill

- Apply on spec PRs whenever `review-spec` is applied.
- Do not apply on code PRs handled by `review-pr`; those use `security-review-pr` instead.
- Skip the skill entirely when the changed spec content has no plausible security surface (e.g. purely editorial wording changes, typo fixes, or doc structure cleanup). It is better to stay silent than to manufacture findings.
- Do not duplicate findings the base `review-spec` pass will already raise. If the base review would naturally catch an issue, leave it there rather than re-reporting it from the security pass.

## Security concerns to audit

Evaluate the changed spec content against the following concerns. Treat the list as a checklist, not a ceiling — flag other clearly security-relevant design issues when they appear. Stay at the design-doc level: worry about what the spec does or does not commit to, not how it will be coded.

### Threat surface and trust boundaries
- New external inputs, endpoints, webhooks, CLI surfaces, or file formats that are introduced without describing who can reach them and under what trust assumptions.
- Trust boundaries that are implied but not explicitly stated (e.g. "the agent receives data from GitHub" without saying which fields are attacker-controlled).
- User-supplied or third-party content (issues, comments, spec bodies, uploaded files, remote URLs) that will flow into automation, prompts, commands, or storage without a clear validation or sanitization plan.
- Features that expand what an unauthenticated or low-privilege actor can cause the system to do.

### Authentication and authorization model
- New actors, roles, or automation identities introduced without a clear description of how they authenticate and what they are allowed to do.
- Authorization rules that are described informally ("only maintainers can trigger this") without specifying how that is enforced.
- Privilege escalation risks: features where a less-privileged user can cause a more-privileged actor (bot, workflow, agent) to act on their behalf without explicit gating.
- Missing discussion of how permission or ownership changes propagate (e.g. revoking access, rotating tokens, removing a collaborator).

### Sensitive data handling and privacy
- New data the system will collect, store, log, or transmit without stating sensitivity, retention, or access controls.
- Personally identifiable information, auth tokens, session identifiers, private repository contents, or customer data routed through logs, analytics, prompts, or third-party services without a redaction plan.
- Specs that assume data is "internal" without describing the boundary that keeps it internal.
- Missing discussion of how the feature behaves for private repositories, restricted orgs, or data subject to deletion requests.

### Secrets and key management
- New credentials, API keys, signing keys, or tokens introduced without describing where they live, who can read them, and how they are rotated.
- Specs that describe passing secrets through environment variables, command-line arguments, or log-visible paths without acknowledging the exposure.
- Shared secrets across environments (dev, staging, prod) where the spec does not call out isolation.
- Missing discussion of what happens when a secret is leaked or revoked.

### Abuse, misuse, and denial of service
- Features that can be triggered by external events (webhooks, comments, scheduled jobs) without describing rate limiting, deduplication, or cost controls.
- Automation loops where attacker-controlled input can cause unbounded work, recursive invocations, or expensive downstream calls.
- Agent or LLM-driven flows where untrusted input can be interpreted as instructions (prompt injection) without a mitigation described in the spec.
- Missing discussion of what happens under partial failure (retries, duplicate side effects, poisoned queues).

### Dependencies and supply chain
- New third-party services, registries, models, or binaries introduced without describing trust assumptions or pinning strategy.
- Plans to execute code or scripts fetched at runtime (remote scripts, downloaded binaries, dynamic imports) without integrity verification.
- Vendor or tool choices that materially change the repository's trust boundary without calling that out.

### Configuration and defaults
- New configuration options or feature flags whose default value is insecure (auth optional, TLS off, public by default) without explicit justification.
- Specs that leave important defaults unspecified when the safe choice is not obvious.
- CORS, cookie, header, or file-permission decisions implied by the design but not written down.

### Observability and incident response
- Specs that introduce security-relevant operations (auth, secret use, privileged actions) without describing what is logged, how logs are protected, and how an operator would notice abuse.
- Missing discussion of how to detect and respond to the specific failure modes introduced by the feature.

## How to evaluate

1. Read `pr_description.txt` and `pr_diff.txt` to understand the scope and intent of the spec change.
2. For each changed section, ask: if this were implemented as written, which of the concerns above would a security-minded reviewer raise?
3. Distinguish between "the spec is silent on X" (usually flag) and "the spec explicitly accepts risk X" (usually acceptable if the reasoning is sound).
4. Prefer evidence-based findings tied to specific changed lines or sections. If a concern only applies to untouched spec content, describe it in the review summary instead of as an inline comment.
5. Do not flag purely editorial or non-security issues here — those belong in the base `review-spec` pass.
6. Do not repeat findings already covered by the base review; if the base pass would naturally catch it, leave it there.
7. Do not treat a spec as insecure just because it does not exhaustively enumerate every threat. Focus on concerns that would plausibly lead to an insecure implementation or a missed mitigation.

## How to report findings

- Do not create a separate report file.
- Fold security findings into the same `review.json` produced by `review-spec`.
- Prefix every security finding's comment body with a `[SECURITY]` tag after the severity label so reviewers can tell the source of the concern. For example:
  - `🚨 [CRITICAL] [SECURITY] Spec allows untrusted input into shell command without validation: ...`
  - `⚠️ [IMPORTANT] [SECURITY] Authentication model for new webhook is unspecified: ...`
  - `💡 [SUGGESTION] [SECURITY] Consider documenting token rotation strategy: ...`
- In the review summary, add a dedicated `## Security` subsection when there are security findings. List the most important security concerns there in addition to any inline comments. If there are no security findings, do not add the subsection.
- Count security findings toward the existing `Found: X critical, Y important, Z suggestions` tally in the summary. Do not add a separate security counter.
- Upgrade the overall verdict if a security finding materially demands it. A critical security finding in a spec should generally result in `Request changes` so the design gap is resolved before implementation.

## Severity mapping

- `🚨 [CRITICAL]` for design choices that would almost certainly produce an exploitable implementation (e.g. feeding untrusted issue bodies directly into a shell command, auth explicitly optional on a destructive action, storing plaintext credentials).
- `⚠️ [IMPORTANT]` for design gaps that should be resolved before implementation (e.g. missing authentication model for a new surface, unspecified handling of private-repo data, absent rate limiting on an externally triggerable flow).
- `💡 [SUGGESTION]` for defense-in-depth improvements or documentation gaps that would strengthen the spec but are not blockers (e.g. calling out token rotation, documenting log redaction).
- `🧹 [NIT]` is rarely appropriate for security findings; use only when the comment includes a concrete rewrite and the issue is genuinely cosmetic.

## Inline comment requirements

- Follow the same diff-line rules as `review-spec`: inline comments must target lines that exist in this PR's diff.
- Keep comments concise, direct, and actionable. Explain the concern, then the fix the spec should adopt.
- When proposing a concrete spec rewrite, use the same `suggestion` block format as `review-spec`.

## Boundaries

- Do not perform code-level review; this skill is scoped to spec prose and design decisions.
- Do not run dynamic scans, fetch remote advisories, or call external security APIs.
- Do not speculate about vulnerabilities that cannot be tied to the diff or the checked-out spec files.
- Do not gate the PR on theoretical risks; prefer `💡 [SUGGESTION]` when the risk is low or the mitigation is optional.
- Do not post to GitHub directly. Your only output is the merged `review.json` from the base review pass.
