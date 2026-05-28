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

目标 agent login 来自 workflow input `agent_login`，未提供时使用仓库 Actions
variable `AGENT_LOGIN`。`SPEC_AGENT_LOGIN` 不再作为该 workflow 的配置入口。

手动触发同样必须满足 `ready-to-spec` 与目标 agent assignment 条件。若 issue
已经带有 `ready-to-implement`，spec workflow 不再启动，避免同一个 issue 同时进入
spec 与 implementation 阶段。

## Spec PR 后续 review

当 workflow 创建或更新 spec PR 并产生实际 diff 后，会显式触发 AI PR Review
workflow review 该 spec PR。该显式触发用于覆盖 GitHub 对 `GITHUB_TOKEN` 创建 PR
后的递归 workflow 触发限制；是否真正执行 review 仍由 AI PR Review workflow
自身的 draft 与同仓库 head 条件决定。

来源：PR #56，PR #58，PR #65。
