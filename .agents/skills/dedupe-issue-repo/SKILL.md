---
name: dedupe-issue-repo
specializes: dedupe-issue
description: Repo-specific dedupe guidance . Only the categories declared overridable by the core dedupe-issue skill may be specialized here.
---

# Repo-specific dedupe guidance

This file is a companion to the core `dedupe-issue` skill. It does not
redefine the duplicate-detection algorithm, the similarity thresholds,
or the output contract. It only specializes the override categories the
core skill marks as overridable.

## Known-duplicate clusters

No known-duplicate clusters have been captured for this repository yet.
The weekly `update-dedupe` loop will propose additions here over time
when maintainers repeatedly close issues as duplicates of the same
canonical thread.
