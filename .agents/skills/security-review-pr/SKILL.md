---
name: security-review-pr
description: Audit a pull request diff for common security concerns (input validation, sanitization, authentication and authorization, secrets management, unsafe dependencies, and related risks) and fold findings into the same review.json produced by the base PR review. Use as a supplement to `review-pr` whenever a code PR is being reviewed.
---

# Security Review PR Skill

Audit the current pull request for security concerns and fold any findings into the same `review.json` produced by the base `review-pr` skill.

## Goal

Provide a focused security pass on top of the general PR review. This is a supplement to `review-pr`, not a separate output. Findings must be merged into the single combined `review.json` so reviewers receive one cohesive review.

## Context

- The working directory is the PR branch checkout.
- The workflow usually provides an annotated diff in `pr_diff.txt`.
- The workflow usually provides the PR description in `pr_description.txt`.
- Focus on the files and lines changed by this PR.
- Default behavior: do not post comments or reviews to GitHub directly.

## When to apply this skill

- Apply on code PRs whenever `review-pr` is applied.
- Do not apply on spec-only PRs handled by `review-spec`.
- Skip the skill entirely when no changed file introduces code or configuration that touches the concerns below; it is better to stay silent than to manufacture findings.
- Do not duplicate findings the base `review-pr` pass will already raise. If the base review would naturally catch an issue, leave it there rather than re-reporting it from the security pass.

## Security concerns to audit

Evaluate each changed hunk against the following concerns. Treat the list as a checklist, not a ceiling — flag other clearly security-relevant issues when they appear.

### Input validation and untrusted data
- User-supplied or network-supplied input used without validation, length limits, or type checks.
- Deserialization of untrusted data (e.g. `pickle`, `yaml.load`, `eval`, `Function`, `JSON.parse` feeding into a command).
- Path traversal risk: user input concatenated into filesystem paths without normalization or an allowlist.
- SSRF risk: user-controlled URLs passed to outbound HTTP clients without scheme or host restrictions.
- Unbounded resource use driven by untrusted input (memory, loops, regex with catastrophic backtracking).

### Output encoding and sanitization
- Untrusted data interpolated into SQL, shell commands, HTML, Markdown, log lines, or URLs without the right encoding or parameterization.
- Use of `shell=True`, string concatenation into `exec`/`spawn`, or raw SQL strings.
- Rendering user-supplied Markdown or HTML into a UI without sanitization.

### Authentication and authorization
- Missing or weakened authentication checks on new endpoints, RPC handlers, or CLI commands.
- Authorization checks that trust client-supplied identifiers instead of the authenticated principal.
- Permission checks removed or made more permissive without clear justification.

### Secrets management
- Hardcoded credentials, API keys, private keys, or tokens committed in source.
- Secrets read from insecure locations (world-readable files, logs, environment dumps printed to stdout).
- Secrets passed via command-line arguments where they would leak into process listings or shell history.
- Secrets written to logs, error messages, analytics events, or serialized payloads.
- New secrets added to `.env`, fixtures, or test data that are real rather than clearly synthetic placeholders.

### Cryptography and randomness
- Use of weak or deprecated primitives (MD5, SHA1 for security purposes, ECB mode, RC4).
- Hand-rolled crypto when a vetted library is available.
- Non-cryptographic randomness (`random.random`, `Math.random`) used for tokens, IDs, or security decisions.
- Missing integrity or authenticity checks when decrypting or verifying tokens.

### Dependencies and supply chain
- New dependencies from unknown registries or forks without a clear rationale.
- Pinning loosened in a way that allows untrusted upgrades (e.g. `*` or very broad ranges on a sensitive package).
- Fetching scripts over HTTP or piping curl to a shell inside build or CI steps.

### Data handling and privacy
- Logging or echoing personally identifiable information, auth tokens, session IDs, or request bodies that may contain them.
- New telemetry or analytics events that capture sensitive data without redaction.
- Expanding the scope of stored data beyond what the feature requires.

### Configuration and defaults
- New feature flags or configuration options that default to insecure values (e.g. TLS disabled, auth optional).
- CORS, cookies, or headers weakened in scope without an explicit justification.
- Permissive file modes on newly created files that contain sensitive material.

## How to evaluate

1. Read `pr_description.txt` and `pr_diff.txt` to understand the scope and intent of the change.
2. For each changed hunk, consider which of the concerns above could plausibly apply given the surrounding code in the checkout.
3. Prefer evidence-based findings tied to specific changed lines. If a concern only applies to untouched code, describe it in the review summary instead of as an inline comment.
4. Do not flag purely stylistic or non-security issues here — those belong in the base `review-pr` pass.
5. Do not repeat findings already covered by the base review; if the base pass would naturally catch it, leave it there.

## How to report findings

- Do not create a separate report file.
- Fold security findings into the same `review.json` produced by `review-pr`.
- Prefix every security finding's comment body with a `[SECURITY]` tag after the severity label so reviewers can tell the source of the concern. For example:
  - `🚨 [CRITICAL] [SECURITY] SQL injection: ...`
  - `⚠️ [IMPORTANT] [SECURITY] Secret written to logs: ...`
  - `💡 [SUGGESTION] [SECURITY] Prefer parameterized query: ...`
- In the review summary, add a dedicated `## Security` subsection when there are security findings. List the most important security concerns there in addition to any inline comments. If there are no security findings, do not add the subsection.
- Count security findings toward the existing `Found: X critical, Y important, Z suggestions` tally in the summary. Do not add a separate security counter.
- Upgrade the overall verdict if a security finding materially demands it. A critical security finding should generally result in `Request changes`.

## Severity mapping

- `🚨 [CRITICAL]` for issues that are likely exploitable in production (e.g. shell injection with attacker-controlled input, committed live secret, missing auth on a destructive endpoint).
- `⚠️ [IMPORTANT]` for plausible security weaknesses that should be fixed before merge (e.g. missing input validation on an internal-only endpoint, weak hashing for non-password data, overly broad CORS).
- `💡 [SUGGESTION]` for defense-in-depth improvements that are clearly worthwhile but not immediate risks.
- `🧹 [NIT]` is rarely appropriate for security findings; use only when the comment includes a concrete suggestion block and the issue is genuinely cosmetic.

## Inline comment requirements

- Follow the same diff-line rules as `review-pr`: inline comments must target lines that exist in this PR's diff.
- Keep comments concise, direct, and actionable. Explain the threat, then the fix.
- When proposing code changes, use the same `suggestion` block format as `review-pr`.

## Boundaries

- Do not run dynamic scans, fetch remote advisories, or call external security APIs.
- Do not speculate about vulnerabilities that cannot be tied to the diff or the checked-out files.
- Do not gate the PR on theoretical risks; prefer `💡 [SUGGESTION]` when the risk is low or the fix is optional.
- Do not post to GitHub directly. Your only output is the merged `review.json` from the base review pass.
