---
type: concept
title: Repo-specific duplicate guidance
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/dedupe-guidance-companion.md
  - docs/product/raw/issue-triage-workflow.md
  - docs/product/raw/update-dedupe-workflow.md
---

# Repo-specific duplicate guidance

Repo-specific duplicate guidance 为 issue triage 保存仓库本地重复模式，但不改变 core `dedupe-issue` 的高精度契约。

## 当前规则

- companion 位于 `.agents/skills/dedupe-issue-repo/SKILL.md`。
- 只能 specialize core skill 明确允许覆盖的 categories。
- 不重新定义算法、阈值、候选要求、安全规则或输出契约。
- triage 使用 workflow 提供的 `dedupe_candidates.json` 作为权威候选列表。
- companion 不能授权 agent 额外抓取 GitHub issues 或降低重复证据门槛。
- 当前没有已捕获的 known-duplicate clusters。

## 更新边界

- 后续 clusters 应记录 canonical issue 和稳定 signals。
- guidance 应短小可 review，不保存原始 GitHub history 或一次性案例。
- 只能由受控 self-improvement flows 基于强维护者 duplicate 证据更新 companion。
- 不得修改 core `dedupe-issue` skill 或削弱 precision-over-recall 行为。
- `update-dedupe` workflow 只从维护者确认的 repeated duplicate clusters 学习规则；证据不足、没有 repeated cluster 或已有 guidance 覆盖时产出 `no_change`。
- update flow 的持久写入范围仅限 `.agents/skills/dedupe-issue-repo/`，不能修改 core `dedupe-issue`。

## Supporting Summaries

- [Repo-specific dedupe guidance companion 摘要](../summaries/dedupe-guidance-companion.md)
- [Issue triage workflow 摘要](../summaries/issue-triage-workflow.md)
- [update-dedupe workflow 摘要](../summaries/update-dedupe-workflow.md)

## Related Concepts

- [Issue triage workflow](issue-triage-workflow.md)
- [Issue triage 结果契约](issue-triage-result-contract.md)
- [update-dedupe 自进化规则 workflow](update-dedupe-workflow.md)
