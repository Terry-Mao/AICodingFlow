# 产品变更报告

产品变更报告是对已合并仓库变更的时间序列摘要。报告生成在
`docs/updates/` 下，应从稳定的产品层面描述已交付行为、影响、风险和验证，
但不作为产品行为的权威来源。

## 生成流程

`product-change-report` skill 和配套 GitHub Actions workflow 负责生成产品变更报告。
workflow 可以手动触发，也可以按计划运行；每次运行按 UTC 日期扫描对应日历日内已合并的
PR，并按 mergedAt 升序、PR 编号升序处理。

手动运行可以使用单日 `report_date`，也可以使用 `start_date` 与 `end_date` 做历史回填。
历史回填按 UTC 日期区间扫描，其中 `start_date` 为包含边界，`end_date` 为不包含边界；单日
日期不能与区间输入混用，区间输入必须同时提供开始与结束日期，且结束日期必须晚于开始日期。

单日报告路径为 `docs/updates/auto-update-YYYY-MM-DD.md`。跨日报告使用
`docs/updates/auto-update-YYYY-MM-DD-to-YYYY-MM-DD.md`，其中后一个日期是区间内最后一个
被包含的 UTC 日期。生成上下文包括 merged PR、commit diff、PR description、linked issue、
已存在的 product docs 和相关 specs。报告应只把已合并、可验证的变化写成时间序列摘要；
可能需要长期产品文档同步的内容只能作为候选项记录，不能由该 skill 直接改写 `docs/product/`。

## 报告语言

生成或更新产品变更报告时，`product-change-report` 会自动选择报告的主要自然语言。
更新既有报告时，报告会保留该报告已经使用的主要自然语言。创建新报告时，如果已经存在
`docs/updates/auto-update-*.md` 报告，则优先使用最近报告中的主导自然语言。

如果没有既有报告可参考，报告语言会从可报告 PR 的标题、PR body、linked issue、已提交
spec 和相关 product docs 推断。主要为中文的来源上下文生成中文报告，主要为英文的来源上下文
生成英文报告；如果来源上下文混合或不清晰，则优先采用 maintainer-authored docs 和 specs 中的
主导语言，仍不清晰时默认英文。代码标识符、文件路径、标签、分支名、API 名称、PR 编号、URL
和引用的命令输出保持原样。

## 去重记录

外层 workflow 维护 `docs/updates/.product-change-report-ledger.json`，用于记录已经写入报告的
PR，避免同一 merged PR 被重复写入不同日期的报告。同一报告日期的重新运行可以重写或补全同一
report path；已记录到其他 report path 的 PR 会被跳过并作为 already reported context 输出。

ledger entry 会记录处理状态。`reported` 表示对应 PR 已写入报告；`scanned_no_update` 表示
workflow 已扫描该 PR，但没有产出可提交的产品变更报告，例如 Codex 没有生成报告、生成的是空文件、
生成的是完整的“无变化”占位内容，或现有报告没有新增并且没有引用当前 PR。`scanned_no_update`
不会创建产品变更报告 PR，但会让后续扫描避免重复处理同一 PR。

## 职责边界

Codex 在该 workflow 中只负责读取稳定上下文并生成报告文件，不负责 stage、commit、push、
创建或更新 PR，也不负责更新 ledger。外层 workflow 负责校验写入范围、校验上下文 checksum、
更新 ledger，并创建或更新产品变更报告 PR。

`product-change-report` skill 的写入范围只限目标报告文件。它不得修改长期产品文档、
compiled wiki、source specs、workflow 文件或 ledger state。

如果生成结果是空文件或完整的“无变化”占位报告，workflow 会把未跟踪的报告文件移除，并只按
`scanned_no_update` 更新 ledger。已跟踪的既有报告不能被空文件或“无变化”占位报告替换。

创建或更新产品变更报告 PR 时，workflow 只复用同一 head branch 上的 open PR；不会把 closed
PR 当作可更新目标。

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

来源：PR #165，https://github.com/Terry-Mao/AICodingFlow/pull/165；PR #168，https://github.com/Terry-Mao/AICodingFlow/pull/168；PR #171，https://github.com/Terry-Mao/AICodingFlow/pull/171；PR #173，https://github.com/Terry-Mao/AICodingFlow/pull/173；PR #181，https://github.com/Terry-Mao/AICodingFlow/pull/181
