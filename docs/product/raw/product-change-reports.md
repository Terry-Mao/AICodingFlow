# 产品变更报告

产品变更报告是对已合并仓库变更的时间序列摘要。报告生成在
`docs/updates/` 下，应从稳定的产品层面描述已交付行为、影响、风险和验证，
但不作为产品行为的权威来源。

## 生成流程

`product-change-report` skill 和配套 GitHub Actions workflow 负责生成产品变更报告。
workflow 可以手动触发，也可以按计划运行；每次运行按 UTC 日期扫描对应日历日内已合并的
PR，并按 mergedAt 升序、PR 编号升序处理。

报告路径固定为 `docs/updates/auto-update-YYYY-MM-DD.md`。生成上下文包括 merged PR、
commit diff、PR description、linked issue、已存在的 product docs 和相关 specs。报告应只把
已合并、可验证的变化写成时间序列摘要；可能需要长期产品文档同步的内容只能作为候选项记录，
不能由该 skill 直接改写 `docs/product/`。

## 去重记录

外层 workflow 维护 `docs/updates/.product-change-report-ledger.json`，用于记录已经写入报告的
PR，避免同一 merged PR 被重复写入不同日期的报告。同一报告日期的重新运行可以重写或补全同一
report path；已记录到其他 report path 的 PR 会被跳过并作为 already reported context 输出。

## 职责边界

Codex 在该 workflow 中只负责读取稳定上下文并生成报告文件，不负责 stage、commit、push、
创建或更新 PR，也不负责更新 ledger。外层 workflow 负责校验写入范围、校验上下文 checksum、
更新 ledger，并创建或更新产品变更报告 PR。

`product-change-report` skill 的写入范围只限目标报告文件。它不得修改长期产品文档、
compiled wiki、source specs、workflow 文件或 ledger state。

## 来源引用

当引用有助于追踪来源时，报告条目可以引用已合并 PR、GitHub issue URL 或已批准
spec。生成的报告不得包含 commit ID。

当条目引用 related issue 时，必须使用 linked issue metadata 提供的 GitHub
issue URL。仅写 issue 编号不足以构成 related issue 引用。

## 校验行为

报告状态校验会拒绝暴露 commit-like SHA token 的生成报告。对于已 linked 的
related issue，如果报告提到了该 issue 但没有包含 PR metadata 中对应的 GitHub
issue URL，校验也会拒绝该报告。

即使 PR 编号与 linked issue 编号相同，PR 引用仍然有效。在这种情况下，类似
`PR #87` 的来源引用不会被当作 related issue 引用处理。

来源：PR #165，https://github.com/Terry-Mao/AICodingFlow/pull/165；PR #181，https://github.com/Terry-Mao/AICodingFlow/pull/181
