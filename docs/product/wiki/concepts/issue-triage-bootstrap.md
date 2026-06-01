---
type: concept
title: Issue triage 初始化配置
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/bootstrap-issue-config-skill.md
---

# Issue triage 初始化配置

Issue triage 初始化配置为仓库生成长期维护的 label 定义和 ownership hints，让后续分诊 agent 有稳定输入。

## 当前规则

- `bootstrap-issue-config` 生成或更新 `.github/issue-triage/config.json` 和 `.github/CODEOWNERS`。
- `config.json` 顶层只包含 `labels`，每个 label 记录 6 位 hex color 和一句 description。
- 基础标签覆盖 bug/enhancement/documentation、needs-info/duplicate/triaged 和 repro 等级。
- 初始化会合并现有 labels、最近 issues、issue templates、已有配置、CODEOWNERS 和最近贡献记录。
- 初始化是 additive 和幂等的，不删除旧配置、不重复写入已有 CODEOWNERS 行。
- bootstrap 不创建空的 repo companion skills。

## Supporting Summaries

- [Issue triage 初始化配置 skill 摘要](../summaries/bootstrap-issue-config-skill.md)

## Related Concepts

- [Issue triage workflow](issue-triage-workflow.md)
- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)

