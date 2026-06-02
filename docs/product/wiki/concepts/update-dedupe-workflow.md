---
type: concept
title: update-dedupe 自进化规则 workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-02
review_due: 2026-08-31
sources:
  - docs/product/raw/update-dedupe-workflow.md
  - docs/product/raw/dedupe-guidance-companion.md
---

# update-dedupe 自进化规则 workflow

`update-dedupe` workflow 是受控 self-improvement 流程，用维护者确认的重复关闭记录更新 repo-local duplicate guidance。

## 学习入口

- 由维护者通过 `Update Dedupe Guidance` workflow 手动运行。
- 默认扫描最近 7 天的 duplicate 关闭记录，也可通过 workflow inputs 覆盖目标 repo、扫描天数和是否推送更新分支。
- 学习输入必须来自强 duplicate 信号：`state_reason == "duplicate"`，且 timeline 中存在可解析 canonical issue 的 `marked_as_duplicate` 事件。
- 普通评论、标题相似、agent 推断、单个候选匹配或缺少 canonical timeline 事件的记录不能单独触发规则学习。

## 更新条件

- 只有 repeated cluster 才能产生 guidance 更新。
- repeated cluster 表示至少两个独立 issues 被维护者关闭为同一个 canonical issue 的 duplicate，或存在同等强度的维护者结构化证据。
- 证据不足、没有 repeated cluster，或现有 guidance 已覆盖该模式时，产出 `no_change`。
- 证据存在但无法安全解释时，流程产出错误，外层 workflow 停止应用。

## 写入边界

- skill 只写 `update-dedupe-output/` 交接目录。
- 需要更新时，输出 `.agents/skills/dedupe-issue-repo/SKILL.md` 的完整 replacement 内容。
- 持久写入范围仅限 `.agents/skills/dedupe-issue-repo/`。
- 不修改 core `dedupe-issue` skill，不放宽 2-candidate minimum、similarity threshold、输出 schema、候选来源或 precision-over-recall 原则。
- 有 guidance diff 时，runner 使用 `feat/update-dedupe` 创建或更新 PR；没有 guidance diff 时不创建 PR。

## Supporting Summaries

- [update-dedupe workflow 摘要](../summaries/update-dedupe-workflow.md)
- [Repo-specific dedupe guidance companion 摘要](../summaries/dedupe-guidance-companion.md)

## Related Concepts

- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)
- [Issue triage workflow](issue-triage-workflow.md)
- [Issue triage 结果契约](issue-triage-result-contract.md)
