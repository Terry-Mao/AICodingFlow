---
type: summary
title: Repo-specific dedupe guidance companion 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/dedupe-guidance-companion.md
---

# Repo-specific dedupe guidance companion 摘要

Source: [docs/product/raw/dedupe-guidance-companion.md](../../raw/dedupe-guidance-companion.md)

`dedupe-issue-repo` 是 core `dedupe-issue` skill 的仓库本地 companion，用于记录 repository-local duplicate patterns，而不改变核心重复检测契约。

## 作用范围

- companion 文件位于 `.agents/skills/dedupe-issue-repo/SKILL.md`。
- 只能 specialize core `dedupe-issue` 声明可覆盖的 categories。
- 不重新定义 duplicate-detection algorithm、similarity thresholds、candidate requirements、safety rules 或 output contract。
- issue triage 仍使用 workflow 提供的 `dedupe_candidates.json` 作为权威候选列表。
- companion 可指导解释仓库特定重复模式，但不能授权 agent 额外抓取 GitHub issues 或降低重复证据门槛。

## Known-duplicate clusters

- companion 包含 `Known-duplicate clusters` section。
- 创建时本仓库没有已捕获的 known-duplicate clusters。
- 后续新增应标识 canonical issue 和稳定 signals，例如 title patterns、error text、reproduction paths、requested capability 或 key terminology。
- guidance 应保持短小可 review，避免保存原始 GitHub history 或一次性案例。

## 更新边界

- companion 只应由受控 self-improvement flows 基于强维护者 duplicate 证据更新。
- 这些流程可以更新 `.agents/skills/dedupe-issue-repo/SKILL.md`。
- 不得修改 `.agents/skills/dedupe-issue/SKILL.md` 或削弱 core precision-over-recall 行为。

## 支持的概念

- [Repo-specific duplicate guidance](../concepts/repo-specific-duplicate-guidance.md)
- [Issue triage workflow](../concepts/issue-triage-workflow.md)

