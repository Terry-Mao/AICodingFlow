# 自动实现 workflow

自动实现 workflow 用于把已经准备实现的 GitHub issue 派发给 Codex agent，并由外层 GitHub Actions 创建或更新 implementation PR。普通新 issue 不会直接进入实现阶段；issue 需要满足 `ready-to-implement` 与 bot assignment 等触发条件。

## 触发条件与 agent 配置

workflow 可以手动触发，也可以由 issue label、issue assignment 或 issue comment
mention 触发。自动 issue 事件只有在 issue 不是 PR 且满足以下条件时才会继续执行：

- 新增 `ready-to-implement` label 时，issue 必须已经 assign 给目标 agent。
- assign 给目标 agent 时，issue 必须已经带有 `ready-to-implement` label。
- issue comment 显式 mention 目标 agent 时，可以触发已 ready 的 issue。

PR comment 不会触发 implementation workflow；PR comment mention 由 AI PR Review
workflow 处理。

目标 agent login 来自 workflow input `agent_login`，未提供时使用仓库 Actions
variable `AGENT_LOGIN`。`SPEC_AGENT_LOGIN` 与 `IMPLEMENT_AGENT_LOGIN` 不再作为该
workflow 的配置入口。

Spec PR 的 `plan-approved` label 只表示该 PR 可作为实现上下文，不会单独触发
implementation workflow。

## Spec context 与目标分支

workflow 按固定优先级选择实现上下文：

- 若存在带 `plan-approved` 的 spec PR，使用该 PR 的 head branch 作为目标分支，并把实现追加到同一个 PR 分支。
- 若没有 approved spec PR，但默认分支存在 `specs/issue-<issue-number>/` 下的 spec，使用默认分支 spec 作为上下文，目标分支默认为 `spec/implement-issue-<issue_number>`。
- 若没有任何 spec context，workflow 仍可启动实现，但 agent prompt 必须明确说明没有 approved 或 repository spec context。
- 若存在未批准 spec PR 且默认分支没有 specs，workflow 不启动实现，并在 progress comment 中说明没有可用的 approved spec context。

当没有 approved spec PR 时，workflow 可以创建新的 draft implementation PR，也可以更新已有 draft implementation PR。

## Agent 与外层 workflow 职责

agent 负责读取稳定上下文、产出实现 diff、必要时同步 specs，并写出
`implementation_summary.md` 与 `pr-metadata.json`。agent 不直接 commit、push、
创建 PR、更新 PR 或编辑 issue。

`pr-metadata.json` 必须包含 `branch_name`、`pr_title`、`pr_summary` 和
`intended_files`。`intended_files` 是外层 workflow 应提交的 repository-relative
实现文件列表，必须覆盖所有有意修改的 production、test、spec、`.agents` 或 workflow
文件；不得包含 workflow handoff 文件、validation logs、生成缓存文件或未变化文件。

外层 workflow 负责校验 agent 产出的 metadata，提交并推送目标分支，创建或更新
implementation PR，并维护 issue progress comment。提交实现分支时，外层 workflow
只提交通过校验且出现在 `intended_files` 中的实现文件；若实际变更与 `intended_files`
不一致，或包含 Python/cache 等生成文件，workflow 会拒绝提交。

当实现变更包含 `.github/workflows/` 下的 GitHub workflow 文件时，仓库必须配置
`WORKFLOW_UPDATE_TOKEN` secret。外层 workflow 会使用该 token 推送 implementation
分支，以获得 workflow 文件写入权限；若缺少该 secret，包含 workflow 文件的实现提交会在
commit 前被拒绝。普通不修改 GitHub workflow 文件的实现分支继续使用默认
`GITHUB_TOKEN` 推送。

创建或更新 implementation PR 后不会自动触发 AI PR Review，因为 implementation PR
默认保持 draft。需要 review 时，在 PR comment 中 `@AGENT_LOGIN` 手动触发；是否真正执行
review 仍由 AI PR Review workflow 自身的 open、draft 与同仓库 head 条件决定。

来源：PR #52，PR #56，PR #58，PR #67，PR #68，PR #74，`specs/issue-18/product.md`。
