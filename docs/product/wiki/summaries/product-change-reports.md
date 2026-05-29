---
type: summary
title: 产品变更报告摘要
sources:
  - docs/product/raw/product-change-reports.md
---

# 产品变更报告摘要

Source: [docs/product/raw/product-change-reports.md](../../raw/product-change-reports.md)

产品变更报告是对已合并仓库变更的时间序列摘要，生成在 `docs/updates/` 下。报告应从稳定产品层面描述已交付行为、影响、风险和验证，但不作为产品行为的权威来源。

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
