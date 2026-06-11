---
name: triage-issue-repo
specializes: triage-issue
description: Repo-specific triage guidance. Only the categories declared overridable by the core triage-issue skill may be specialized here.
---

# Repo-specific triage guidance

This file is a companion to the core `triage-issue` skill. It does not
redefine the triage output schema, safety rules, or follow-up-question
contract. It only specializes the override categories the core skill
marks as overridable.

## Heuristics

- Distinguish observed symptoms from reporter hypotheses and proposed fixes.
- Before asking any follow-up question, first try to answer it yourself through code inspection, documentation lookup, or web search. Only ask questions that you cannot resolve on your own and that only the reporter would know.
- Ask targeted follow-up questions only for details the agent cannot derive itself and that materially improve triage confidence.
- Prefer issue-specific questions over generic "please share more info" requests.
- For concrete workflow, skill, documentation, or test failures/improvements that already contain enough detail for a product/spec pass, consider `ready-to-spec` during triage. Maintainers repeatedly added this lifecycle label on issues #251, #239, and #134 after initial triage.
- Treat `ready-to-implement` as a later lifecycle label, not a default initial-triage label. Only include it during triage when the issue already has an approved or clearly complete spec/plan, or the maintainer-provided issue context explicitly says implementation is approved. Maintainers added it after spec-readiness signals on issues #239 and #134.

## Label taxonomy

The label taxonomy for this repository is managed in `.github/issue-triage/config.json`. Prefer labels from that configuration, and avoid inventing new labels unless the prompt explicitly allows it.

## Recurring follow-up patterns

No repo-specific follow-up patterns have been captured for this repository yet.
Future updates may add concise, evidence-backed patterns when maintainer
overrides reveal recurring follow-up needs that are actually specific to this
repository.

## Self-Evolution Boundary

The `update-triage` workflow may propose concise updates to this companion skill
when repeated maintainer correction signals across independent issues reveal
stable repo-specific triage guidance. Those updates must stay within the
override categories allowed by the core `triage-issue` skill and cannot change
the core triage contract, output schema, reserved label rules, safety rules, or
duplicate/follow-up exclusivity.
