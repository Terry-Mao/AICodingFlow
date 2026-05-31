# 产品变更报告：2026-05-30

扫描窗口：`2026-05-30T00:00:00Z`（含）至 `2026-05-31T00:00:00Z`（不含）。

## 用户可见变更

- 长期产品文档新增本地 Git helper skills 说明，覆盖 `git-worktree` 的默认 `.worktrees/<branch-slug>` 目录、分支命名、base 选择、fetch 检查、dirty worktree 处理，以及已存在 branch、worktree 或目标目录时停止而不覆盖的安全边界。来源：PR #206，源 PR #94。
- PR review 产品文档补齐本地 review dirty worktree 支持：`review-pr-local` 与 `review-spec-local` 可基于当前 worktree 快照生成 diff，并用 `.local_review_baseline.status` 区分既有业务改动和 review 期间新增的不允许改动。来源：PR #206，源 PR #90。

## 行为变更

- PR review 产品文档补齐安全补充 review 的长期契约：code PR review 会叠加 `security-review-pr`，spec-only PR review 会叠加 `security-review-spec`，安全发现合并进同一个 `review.json`，使用 `[SECURITY]` 标签，并参与最终 verdict 判断。来源：PR #206，源 PR #93。

## 内部工程变更

- Product docs sync PR 继续累计并落地长期产品文档同步决策，本次同步记录了 PR #86 为无需产品文档更新，并将 PR #90、PR #93、PR #94 的 required 决策写入产品文档同步 ledger。来源：PR #206。

## 风险或待验证

- 本次扫描窗口只包含 product-docs-sync 生成的文档同步 PR；报告反映的是长期产品文档在 2026-05-30 的同步结果，不表示源功能均在该日期首次交付。来源：PR #206。

## 可能需要同步的长期文档

- 无新增候选项；本次 reportable 变更本身已经是 `docs/product/raw/` 的长期产品文档同步结果。来源：PR #206。

## Source references

- PR #206: https://github.com/Terry-Mao/AICodingFlow/pull/206
- Source PR #90: https://github.com/Terry-Mao/AICodingFlow/pull/90
- Source PR #93: https://github.com/Terry-Mao/AICodingFlow/pull/93
- Source PR #94: https://github.com/Terry-Mao/AICodingFlow/pull/94
