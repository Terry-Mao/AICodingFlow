---
type: concept
title: Issue triage 结果契约
status: needs-review
confidence: medium
source_status: conflict
owner: product-docs
last_reviewed: 2026-06-11
review_due: 2026-09-09
sources:
  - docs/product/raw/issue-triage-workflow.md
---

# Issue triage 结果契约

`triage_result.json` 是 issue triage agent 的唯一 handoff，外层 workflow 只根据该文件和受控配置同步 GitHub 状态。

## 字段

- `labels`：来自 triage config、需要外层 workflow 同步的 labels。
- `repro`：`high`、`medium`、`low` 或 `unknown`。
- `confidence`：`high`、`medium` 或 `low`。
- `related_files`、`root_cause`、`summary`：记录证据、可能影响范围和分诊结论。
- `follow_up_questions`：最多 5 个对象，每个对象包含 `question` 和 `reasoning`。
- `duplicate_of`：基于 workflow 候选列表识别出的重复 issues；只有 2 个或更多 likely duplicates 时才填充。
- `issue_body`：workflow 要求评论正文时提供 markdown summary，否则为空字符串。

## 互斥与 label 规则

- `follow_up_questions` 与 `duplicate_of` 互斥。
- 重复判断优先；发现重复 issue 时问题列表必须为空。
- 需要 reporter 补充信息时，`duplicate_of` 必须为空。
- `plan-approved` 是受保护 label，结果不得请求添加。
- 重复结果在配置存在 `duplicate` 时必须带 `duplicate`，且不能带 `triaged`。
- 无重复且无 follow-up questions 时，配置存在 `triaged` 则应带 `triaged`。
- 存在 follow-up questions 时，配置存在 `needs-info` 则应带 `needs-info`。

## 待确认

- 待确认：`ready-to-implement` 和 `ready-to-spec` 的最终输出边界需要产品确认。当前 raw source 同时记录 core skill 的 reserved-label 规则和 repo companion 的 lifecycle label guidance，不能把这些 labels 的 triage 输出行为写成 `current` + `verified`。

## Supporting Summaries

- [Issue triage workflow 摘要](../summaries/issue-triage-workflow.md)

## Related Concepts

- [Issue triage workflow](issue-triage-workflow.md)
- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)
