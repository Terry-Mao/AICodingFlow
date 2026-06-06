---
type: summary
title: 产品变更报告摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-06
review_due: 2026-09-04
sources:
  - docs/product/raw/product-change-reports.md
---

# 产品变更报告摘要

Source: [docs/product/raw/product-change-reports.md](../../raw/product-change-reports.md)

产品变更报告是对已合并仓库变更的时间序列摘要，生成在 `docs/updates/` 下。报告应从稳定产品层面描述已交付行为、影响、风险和验证，但不作为产品行为的权威来源。

## 生成流程

- `product-change-report` skill 和配套 GitHub Actions workflow 负责生成报告。
- Workflow 可手动触发，也可按计划运行；每次运行按 UTC 日期扫描对应日历日内已合并 PR，并按 mergedAt 升序、PR 编号升序处理。
- 手动运行可以使用单日 `report_date`，也可以用 `start_date` 与 `end_date` 做历史回填；区间中 `start_date` 包含、`end_date` 不包含。
- 单日路径为 `docs/updates/auto-update-YYYY-MM-DD.md`；跨日报告路径为 `docs/updates/auto-update-YYYY-MM-DD-to-YYYY-MM-DD.md`，后一个日期是区间内最后一个被包含的 UTC 日期。
- 生成上下文包括 merged PR、commit diff、PR description、linked issue、已存在 product docs 和相关 specs。
- 报告只写已合并、可验证的变化；可能需要长期产品文档同步的内容只能作为候选项记录，不能由该 skill 直接改写 `docs/product/`。

## 报告语言

- 更新既有报告时保留该报告已经使用的主要自然语言。
- 创建新报告时，如果存在 `docs/updates/auto-update-*.md`，优先使用最近报告中的主导自然语言。
- 没有既有报告时，从可报告 PR 标题、PR body、linked issue、已提交 spec 和相关 product docs 推断语言。
- 来源上下文混合或不清晰时，优先采用 maintainer-authored docs 和 specs 的主导语言；仍不清晰时默认英文。
- 代码标识符、路径、标签、分支名、API 名称、PR 编号、URL 和引用命令输出保持原样。

## 去重记录与职责边界

- 外层 workflow 维护 `docs/updates/.product-change-report-ledger.json`，避免同一 merged PR 被重复写入不同日期的报告。
- Ledger entry 使用 `reported` 记录已写入报告的 PR，使用 `scanned_no_update` 记录已扫描但没有可提交报告的 PR。
- `scanned_no_update` 不创建产品变更报告 PR，但会让后续扫描避免重复处理同一 PR。
- Codex 只负责读取稳定上下文并生成目标报告文件，不负责 stage、commit、push、创建或更新 PR，也不更新 ledger。
- `product-change-report` skill 的写入范围只限目标报告文件，不得修改长期产品文档、compiled wiki、source specs、workflow 文件或 ledger state。
- 空文件或完整“无变化”占位报告会被 workflow 作为 no-update 处理；已跟踪报告不能被空文件或占位报告替换。
- 创建或更新产品变更报告 PR 时，workflow 只复用同一 head branch 上的 open PR，不把 closed PR 当作可更新目标。

## 来源引用

- 当引用有助于追踪来源时，报告条目可以引用已合并 PR、GitHub issue URL 或已批准 spec。
- 生成的报告不得包含 commit ID。
- related issue 引用必须使用 linked issue metadata 提供的 GitHub issue URL。
- 只写 issue 编号不足以构成 related issue 引用。

## 校验行为

- 报告状态校验会拒绝暴露 commit-like SHA token 的生成报告。
- 对于已 linked 的 related issue，如果报告提到了该 issue 但没有包含 PR metadata 中对应的 GitHub issue URL，校验会拒绝该报告。
- 即使 PR 编号与 linked issue 编号相同，PR 引用仍有效；类似 `PR #87` 的来源引用不会被当作 related issue 引用处理。

## 支持的概念

- [产品变更报告](../concepts/product-change-reports.md)
