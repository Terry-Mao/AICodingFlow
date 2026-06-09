---
type: concept
title: 本地 PR review 入口
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-09
review_due: 2026-09-07
sources:
  - docs/product/raw/pr-review-verdict.md
---

# 本地 PR review 入口

本地开发完成但尚未 push 或创建 PR 时，可以在当前分支运行与 GitHub review workflow 一致的评审流程。

## 本地 skill

- code review 使用 `review-pr-local`。
- spec-only review 使用 `review-spec-local`。
- 两个本地 skill 会先准备根目录快照，再分别委托给 `review-pr-repo` 或 `review-spec-repo`。
- 仓库本地 wrapper skill 补充本仓库评审偏好，不改变核心输出契约。

## 输入与输出快照

本地 review 输入与输出固定在仓库根目录：

- `pr_description.txt`
- `pr_diff.txt`
- `spec_context.md`，仅 code review 需要且存在可用 spec context 时生成
- `.local_review_baseline.status`
- `review.json`

## 工作树与写入约束

- 本地 review 准备阶段支持当前 worktree 中已有 staged、unstaged 和未跟踪文件改动。
- 准备脚本会删除旧的 review 快照，并基于当前 worktree 相对选定 base 的完整状态生成 `pr_diff.txt`。
- 未被 Git ignore 的未跟踪文件会纳入 diff；根目录 review 快照文件和 `.local_review_baseline.status` 不会纳入 diff。
- `.local_review_baseline.status` 记录准备阶段完成后的业务文件 dirty 状态，并被 Git ignore。
- review 阶段只能写入受控 review 输出文件。
- review 阶段不得修改源码、workflow、测试、spec 或 skill 文件。
- 校验会允许 baseline 中已存在的业务文件状态继续存在，但会拒绝新增业务文件改动、业务文件状态变化、staged 输出、非 review 快照文件变更，以及 review 输出被意外删除。

## Diff 与 spec context

- 本地 review 的 base 可以显式传入；显式 base 拥有最高优先级。
- 未显式传入 base 时，已有 GitHub PR 的当前分支优先使用该 PR 的 base SHA。
- 没有可用 PR base SHA 时，本地 fallback 按 `origin/main`、`upstream/main`、`main` 的优先级解析。
- 当 worktree 没有未提交修改时，本地 diff 仍表示当前 head 相对 base 的提交差异；同时存在已提交和未提交修改时，本地 diff 覆盖两者合并后的当前文件状态。
- code review 会根据本地 diff 中的 changed files 解析 spec context。
- spec-only review 不生成 spec context。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [PR review verdict](pr-review-verdict.md)
- [本地 Git helper skills](local-git-helper-skills.md)
