# 产品变更报告

产品变更报告是对已合并仓库变更的时间序列摘要。报告生成在
`docs/updates/` 下，应从稳定的产品层面描述已交付行为、影响、风险和验证，
但不作为产品行为的权威来源。

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

来源：PR #181，https://github.com/Terry-Mao/AICodingFlow/pull/181
