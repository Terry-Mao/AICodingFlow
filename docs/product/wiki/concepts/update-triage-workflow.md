---
type: concept
title: update-triage 自进化 triage 规则 workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-10
review_due: 2026-09-08
sources:
  - docs/product/raw/update-triage-workflow.md
---

# update-triage 自进化 triage 规则 workflow

`update-triage` workflow 是受控 self-improvement 流程，用维护者在 bot triage 之后的稳定修正信号更新 repo-local triage guidance。

## 学习入口

- 由维护者通过 `Update Triage Guidance` workflow 手动运行。
- 默认扫描最近 7 天内有更新、且能可靠定位 bot triage 时间的 issues。
- Inputs 可覆盖扫描天数、指定单个 issue 用于调试，并控制是否推送更新分支。
- 候选 issue 必须能定位 `triaged_at`；定位来源优先为 bot triage comment marker，其次为 bot 添加 `triaged` label 的 timeline event。
- 聚合只学习 `created_at > triaged_at` 的维护者 label added / removed、reopened 事件和后续评论。
- 维护者身份来自 `OWNER`、`MEMBER`、`COLLABORATOR` 或可验证组织成员 fallback；bot actor 和普通 reporter 评论默认不作为学习信号。
- Duplicate 关闭信号由 `update-dedupe` 负责，不进入 triage guidance 学习。

## 更新条件

- 默认至少两个独立 issues 支持同一模式，才认为证据足够。
- 可学习模式包括 label 分类、area 判断、issue shape heuristic、复现度默认值或同类 follow-up question。
- 证据不足、只有一次性 override、现有 guidance 已覆盖，或全部信号属于 duplicate 学习范围时，流程产出 `no_change`。
- 证据存在但无法安全解释时，流程产出 `error`，外层 workflow 停止应用。

## 写入边界

- Skill 只写临时 `update-triage-output/` 交接目录。
- 持久写入范围仅限 `.agents/skills/triage-issue-repo/SKILL.md` 和 `.github/issue-triage/config.json`。
- 普通 triage heuristic 写入 `.agents/skills/triage-issue-repo/SKILL.md`。
- 只有稳定模式说明 label taxonomy 需要新增 label、重命名 label 或澄清 description 时，才允许最小化更新 `.github/issue-triage/config.json`。
- 不修改 core `triage-issue` skill、`dedupe-issue-repo` companion、workflow 文件、脚本、测试、README 或产品代码。
- 有 guidance diff 时，runner 使用 `feat/update-triage` 创建或更新 PR；没有 guidance diff 时不创建 PR。

## Supporting Summaries

- [update-triage workflow 摘要](../summaries/update-triage-workflow.md)

## Related Concepts

- [Issue triage workflow](issue-triage-workflow.md)
- [Issue triage 结果契约](issue-triage-result-contract.md)
- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)
- [update-dedupe 自进化规则 workflow](update-dedupe-workflow.md)
