---
type: concept
title: 产品变更报告
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-06
review_due: 2026-09-04
sources:
  - docs/product/raw/product-change-reports.md
---

# 产品变更报告

产品变更报告是对已合并仓库变更的时间序列摘要，生成在 `docs/updates/` 下。它描述已交付行为、影响、风险和验证，但不作为产品行为的权威来源。

## 生成与回填

- `product-change-report` skill 和配套 workflow 生成报告，可手动触发或按计划运行。
- 每次运行按 UTC 日期扫描已合并 PR，并按 mergedAt 升序、PR 编号升序处理。
- 手动运行支持单日 `report_date`，也支持 `start_date` 到 `end_date` 的历史回填；区间开始包含、结束不包含。
- 单日报告写入 `docs/updates/auto-update-YYYY-MM-DD.md`；跨日报告写入 `docs/updates/auto-update-YYYY-MM-DD-to-YYYY-MM-DD.md`。
- 报告只写已合并、可验证的变化；长期产品文档同步需求只能作为候选项记录。

## 语言与去重

- 更新既有报告时保留既有主语言。
- 创建新报告时优先继承最近 `docs/updates/auto-update-*.md` 报告的主语言；没有既有报告时从 PR、issue、spec 和 product docs 推断。
- 来源上下文混合或不清晰时，优先采用 maintainer-authored docs 和 specs 的主导语言；仍不清晰时默认英文。
- 外层 workflow 使用 `docs/updates/.product-change-report-ledger.json` 记录 `reported` 与 `scanned_no_update`，避免同一 merged PR 被重复处理。
- `scanned_no_update` 表示已扫描但没有可提交报告，不创建报告 PR，但会阻止后续重复扫描同一 PR。

## 职责边界

- Codex 只生成目标报告文件，不 stage、commit、push、创建或更新 PR，也不更新 ledger。
- `product-change-report` skill 不得修改长期产品文档、compiled wiki、source specs、workflow 文件或 ledger state。
- 空文件或完整“无变化”占位报告不会替换已跟踪报告。
- 创建或更新产品变更报告 PR 时，只复用同一 head branch 上的 open PR。

## 引用规则

- 报告条目可以在有助于追踪时引用已合并 PR、GitHub issue URL 或已批准 spec。
- 生成报告不得包含 commit ID。
- related issue 引用必须使用 linked issue metadata 提供的 GitHub issue URL。
- 只写 issue 编号不足以构成 related issue 引用。

## 校验规则

- 报告状态校验会拒绝暴露 commit-like SHA token 的生成报告。
- 对于已 linked 的 related issue，如果报告提到了该 issue 但没有包含 PR metadata 中对应的 GitHub issue URL，校验会拒绝该报告。
- PR 编号与 linked issue 编号相同也不影响 PR 引用有效性；例如 `PR #87` 不会被当作 related issue 引用处理。

## Supporting Summaries

- [产品变更报告摘要](../summaries/product-change-reports.md)
