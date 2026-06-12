---
name: security-review-pr
description: Audit a pull request diff for common security concerns (input validation, sanitization, authentication and authorization, secrets management, unsafe dependencies, and related risks) and fold findings into the same review.json produced by the base PR review. Use as a supplement to `review-pr` whenever a code PR is being reviewed.
---

# Security Review PR Skill

Audit the current pull request for code-level security concerns and fold any
findings into the same `review.json` produced by `review-pr`.

## Required Contract

Read `.agents/contracts/review.md` and follow it exactly. This skill is a
supplement to `review-pr`; it must not create a separate report, change the
`review.json` schema, loosen diff-line targeting, post to GitHub, call external
security APIs, or regenerate snapshots.

## When To Apply

- Apply on code and mixed PRs whenever `review-pr` is applied.
- Do not apply on spec-only PRs handled by `review-spec`.
- Skip the skill when no changed file introduces code or configuration touching
  the concerns below.
- Do not duplicate findings the base `review-pr` pass will already raise.

## Security Concerns

Evaluate each changed hunk against these concerns. Treat the list as a
checklist, not a ceiling; flag other clearly security-relevant issues when they
appear.

### Input Validation And Untrusted Data

- User-supplied or network-supplied input used without validation, length
  limits, or type checks.
- Deserialization of untrusted data, including `pickle`, `yaml.load`, `eval`,
  `Function`, or parsed JSON flowing into commands.
- Path traversal from user input concatenated into filesystem paths without
  normalization or an allowlist.
- SSRF from user-controlled URLs passed to outbound HTTP clients without scheme
  or host restrictions.
- Unbounded resource use driven by untrusted input.

### Output Encoding And Sanitization

- Untrusted data interpolated into SQL, shell commands, HTML, Markdown, log
  lines, or URLs without proper encoding or parameterization.
- Use of `shell=True`, string concatenation into process execution, or raw SQL
  strings.
- Rendering user-supplied Markdown or HTML without sanitization.

### Authentication And Authorization

- Missing or weakened authentication on new endpoints, RPC handlers, workflow
  triggers, or CLI commands.
- Authorization checks that trust client-supplied identifiers instead of the
  authenticated principal.
- Permission checks removed or made more permissive without clear
  justification.

### Secrets, Crypto, And Sensitive Data

- Hardcoded credentials, API keys, private keys, tokens, or realistic secrets in
  fixtures.
- Secrets read from insecure locations, passed via command-line arguments, or
  written to logs, errors, analytics, or serialized payloads.
- Weak or deprecated primitives used for security, hand-rolled crypto, or
  non-cryptographic randomness used for tokens or security decisions.
- Logging or storing personally identifiable information, auth tokens, session
  IDs, or request bodies that may contain them without redaction.

### Dependencies, Supply Chain, And Defaults

- New dependencies from unknown registries or forks without rationale.
- Loosened pinning that allows untrusted upgrades for sensitive packages.
- Fetching scripts over HTTP or piping downloaded content to a shell.
- Feature flags or configuration options that default to insecure values.
- Weakened CORS, cookie, header, TLS, or file-permission settings.

## Reporting

- Prefix every security finding's comment body with `[SECURITY]` after the
  severity label, for example `⚠️ [IMPORTANT] [SECURITY] Secret written to logs: ...`.
- Add a `## Security` subsection to the top-level review body only when there
  are security findings.
- Count security findings toward the same review summary and verdict. A critical
  security finding should generally produce `REJECT`.
- Tie findings to changed lines when possible. Put broad or untouched-code
  security concerns in top-level `body`.

## Boundaries

- Do not run dynamic scans, fetch remote advisories, or call external security
  APIs.
- Do not speculate about vulnerabilities that cannot be tied to the diff or
  inspected repository files.
- Do not gate the PR on theoretical risks; prefer `💡 [SUGGESTION]` when the
  risk is low or optional.
