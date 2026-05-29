# 自动 spec workflow

自动 spec workflow 用于把准备进入规格设计阶段的 GitHub issue 派发给 Codex
agent，并由外层 GitHub Actions 创建或更新 spec PR。普通新 issue 不会直接进入
spec 创建；issue 需要先满足 ready label 与目标 agent 触发条件。

## 触发条件与 agent 配置

workflow 可以手动触发，也可以由 issue label、issue assignment 或 issue comment
mention 触发。自动 issue 事件只有在 issue 不是 PR 且满足以下条件时才会继续执行：

- 新增 `ready-to-spec` label 时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-spec` label。
- issue comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。

PR comment 不会触发 spec workflow；PR comment mention 由 AI PR Review workflow
处理。

目标 agent login 来自 workflow input `agent_login`，未提供时使用仓库 Actions
variable `AGENT_LOGIN`。`SPEC_AGENT_LOGIN` 不再作为该 workflow 的配置入口。

手动触发同样必须满足 `ready-to-spec` 与目标 agent assignment 条件。若 issue
已经带有 `ready-to-implement`，spec workflow 不再启动，避免同一个 issue 同时进入
spec 与 implementation 阶段。

## Spec plan approval

维护者在 spec PR 上添加 `plan-approved` label 表示该 plan 内容已批准，可以作为
implementation workflow 的 authoritative spec context。`plan-approved` 不是 merge
gate；spec PR 未 merge 时也可以被实现流程读取。

当 spec PR 获得 `plan-approved` 后，approval workflow 会解析 linked issue，并自动从
该 issue 移除 `ready-to-spec`。如果 linked issue 原本没有 `ready-to-spec`，该同步视为
幂等成功。approval workflow 不会自动添加 `ready-to-implement`；该 label 仍由维护者或
外部流程显式添加。

如果 linked issue 已经同时带有 `ready-to-implement` 且 assign 给目标 agent，approval
workflow 会在完成 `ready-to-spec` 移除后触发 implementation workflow。缺少
`ready-to-implement`、缺少目标 agent assignment 或无法解析 linked issue 时，只完成可
执行的状态同步并跳过 implementation dispatch。

## Spec PR 后续 review

当 workflow 创建或更新 spec PR 并产生实际 diff 后，不会自动触发 AI PR Review。
需要 review 时，在 open 且非 draft PR 的普通 conversation comment 中发送
`@AGENT_LOGIN /review`；是否真正执行 review 仍由 AI PR Review workflow 自身的
open、draft 与同仓库 head 条件决定。

创建或更新 PR 时，workflow 只复用同一 head branch 上的 open PR；不会把 closed
PR 当作可更新目标。

来源：PR #56，PR #58，PR #65，PR #66，PR #67，PR #74，PR #82，PR #84，
`specs/issue-77/product.md`。
