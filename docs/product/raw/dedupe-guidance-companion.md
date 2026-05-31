# Repo-specific dedupe guidance companion

`dedupe-issue-repo` is the repository-specific companion for the core
`dedupe-issue` skill. It gives issue triage a durable place to record
repository-local duplicate patterns without changing the core duplicate
detection contract.

## Scope

The companion file lives at `.agents/skills/dedupe-issue-repo/SKILL.md`.
It may specialize only the categories that the core `dedupe-issue` skill
declares overridable. It does not redefine the duplicate-detection algorithm,
similarity thresholds, candidate requirements, safety rules, or output
contract.

Issue triage still uses the workflow-provided `dedupe_candidates.json` as the
authoritative duplicate candidate list. The companion can guide interpretation
of repository-specific duplicate patterns, but it does not authorize the agent
to fetch additional GitHub issues or lower the duplicate evidence bar.

## Known-duplicate clusters

`dedupe-issue-repo` includes a `Known-duplicate clusters` section for concise,
evidence-backed duplicate guidance. At creation time, this repository has no
captured known-duplicate clusters in that companion.

Future additions to this section should identify the canonical issue and the
stable signals that distinguish the duplicate pattern, such as title patterns,
error text, reproduction paths, requested capability, or key terminology. The
guidance should remain short enough to review and should avoid storing raw
GitHub history or one-off cases.

## Update boundary

The companion is intended for controlled self-improvement flows that learn only
from strong maintainer duplicate evidence. Such flows may update
`.agents/skills/dedupe-issue-repo/SKILL.md` when repeated duplicate clusters are
confirmed, but they must not modify `.agents/skills/dedupe-issue/SKILL.md` or
weaken the core precision-over-recall behavior.

来源：PR #128，Issue #125。
