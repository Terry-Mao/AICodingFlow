# 产品变更报告：2026-05-31

扫描窗口：`2026-05-31T00:00:00Z`（含）至 `2026-06-01T00:00:00Z`（不含）。

## 用户可见变更

- 长期产品文档完成一轮大批量同步，补齐自动 implementation workflow、spec workflow、AI PR Review、本地 review、PR comment `/fix` 响应、issue triage、本地 Git helper、CI 失败诊断、merge conflict 处理、bootstrap issue config 和 dedupe companion 等用户/agent 可见能力的 authoritative raw docs。来源：PR #207。
- Product Wiki 随最新 raw docs 重新编译，新增本地 Git helper skills、Comment / manual review status 和安全补充 review 等概念页，并更新 PR review verdict、本地 PR review 入口和索引链接，便于按 Wiki 查询最新产品知识。来源：PR #209。

## Bug fixes

- 长期产品文档修正本地 review 与 PR review 的既有契约：本地 review 可在 dirty worktree 下准备快照，PR comment 或 manual AI PR Review run 会在同仓库 PR head commit 写入 `AI PR Review` commit status，安全补充 review 会并入同一个 `review.json` verdict。来源：PR #207，源 PR #89、PR #90、PR #93。
- 长期产品文档补正 PR comment response workflow：direct push-head 修复不再重写原 PR title/body，响应评论会使用清理后的 `pr_summary`。来源：PR #207，源 PR #120。
- 长期产品文档补充 issue triage duplicate checking 的候选来源：dedupe 使用 workflow 预取的 `dedupe_candidates.json`，覆盖 open 与 recent-closed issue 候选，并排除 pull request。来源：PR #207，源 PR #123。

## 行为变更

- 自动 workflow 文档补齐早期 implementation/spec/review 契约，包括 implementation branch 选择、handoff 文件边界、ready label 与 agent assignment trigger gate、workflow-file push token、spec PR review 触发变化、`@AGENT_LOGIN /review` 命令和 plan approval 后 issue state synchronization。来源：PR #207，源 PR #52、PR #55、PR #56、PR #58、PR #65、PR #66、PR #67、PR #68、PR #74、PR #82。
- 本地 review 文档更新为以 GitHub PR metadata 优先生成 `pr_description.txt`，已有 PR branch 默认使用 PR base SHA，显式 base 会同步到 diff metadata，fallback base 选择优先 `origin/main`。来源：PR #207，源 PR #103、PR #116。
- 本地 Git helper 文档从单一 `git-worktree` 扩展到 `git-branch`、`git-commit` 和 `git-push`，并记录 origin-first base 选择、remote-base `--no-track`、`.worktrees/<branch-name>` 路径语义、fetch/freshness 检查边界和成功创建后默认进入新 worktree 的行为。来源：PR #207，源 PR #94、PR #105、PR #107、PR #109。
- Issue triage 与 bootstrap 文档新增长期行为说明：bootstrap 会生成 label config 与 CODEOWNERS ownership hints；runtime triage 会按触发条件生成 `triage_result.json`，由外层 workflow 同步 labels、duplicate/follow-up comment 和 GitHub 更新。来源：PR #207，源 PR #118、PR #121、PR #123。

## 内部工程变更

- Product change report automation 生成了 `2026-05-29` 的时间序列报告，并在 ledger 中记录该扫描窗口覆盖的 PR，减少后续重复报告。来源：PR #208。
- Product Docs Sync 将多批历史 source PR 的 docs decision 汇总到固定同步 PR，并更新多个 `docs/product/raw/` authoritative docs；本报告只记录同步结果，不修改长期产品文档。来源：PR #207。
- Product Wiki 编译日志增加 2026-05-30 与 2026-05-31 两组派生变更，分别覆盖本地 Git helper、本地 PR review dirty-worktree 入口、comment/manual review status 和 security review supplements。来源：PR #209。

## 风险或待验证

- PR #207 一次性补齐较多历史产品契约；后续如果 raw docs、Wiki 派生页或旧报告之间出现冲突，应以 `docs/product/raw/` 和已合并实现为准，并由后续 Product Wiki 编译或 Product Docs Sync 修正。来源：PR #207、PR #209。
- Product Wiki 仍保留待确认项：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。来源：PR #209。

## 可能需要同步的长期文档

- 本窗口的长期产品文档同步已经由 PR #207 写入 `docs/product/raw/`；如 README、安装说明或 Wiki 之外的衍生材料仍引用旧的 clean-worktree review、裸 mention review、自动 spec PR review、旧 Git helper base 顺序或缺少 `/fix` workflow，应在后续文档同步中校准。来源：PR #207、PR #209。

## Source references

- PR #207: https://github.com/Terry-Mao/AICodingFlow/pull/207
- PR #208: https://github.com/Terry-Mao/AICodingFlow/pull/208
- PR #209: https://github.com/Terry-Mao/AICodingFlow/pull/209
- Source PR #52: https://github.com/Terry-Mao/AICodingFlow/pull/52
- Source PR #55: https://github.com/Terry-Mao/AICodingFlow/pull/55
- Source PR #56: https://github.com/Terry-Mao/AICodingFlow/pull/56
- Source PR #58: https://github.com/Terry-Mao/AICodingFlow/pull/58
- Source PR #65: https://github.com/Terry-Mao/AICodingFlow/pull/65
- Source PR #66: https://github.com/Terry-Mao/AICodingFlow/pull/66
- Source PR #67: https://github.com/Terry-Mao/AICodingFlow/pull/67
- Source PR #68: https://github.com/Terry-Mao/AICodingFlow/pull/68
- Source PR #74: https://github.com/Terry-Mao/AICodingFlow/pull/74
- Source PR #82: https://github.com/Terry-Mao/AICodingFlow/pull/82
- Source PR #89: https://github.com/Terry-Mao/AICodingFlow/pull/89
- Source PR #90: https://github.com/Terry-Mao/AICodingFlow/pull/90
- Source PR #93: https://github.com/Terry-Mao/AICodingFlow/pull/93
- Source PR #94: https://github.com/Terry-Mao/AICodingFlow/pull/94
- Source PR #103: https://github.com/Terry-Mao/AICodingFlow/pull/103
- Source PR #105: https://github.com/Terry-Mao/AICodingFlow/pull/105
- Source PR #107: https://github.com/Terry-Mao/AICodingFlow/pull/107
- Source PR #109: https://github.com/Terry-Mao/AICodingFlow/pull/109
- Source PR #116: https://github.com/Terry-Mao/AICodingFlow/pull/116
- Source PR #118: https://github.com/Terry-Mao/AICodingFlow/pull/118
- Source PR #120: https://github.com/Terry-Mao/AICodingFlow/pull/120
- Source PR #121: https://github.com/Terry-Mao/AICodingFlow/pull/121
- Source PR #123: https://github.com/Terry-Mao/AICodingFlow/pull/123
