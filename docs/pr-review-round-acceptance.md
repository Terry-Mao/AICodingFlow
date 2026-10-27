# PR Review 跨轮次线上验收

此文件只用于 [#295](https://github.com/Terry-Mao/AICodingFlow/issues/295) 的临时测试 PR，完成验收后关闭 PR，不合并到 `main`。

## 验收目标

1. 同一 base/head 快照重复触发时，不新增 Bot Review。
2. 第 1 至第 3 轮的 `review_round_context.json` 均为 `full`。
3. 第 4 轮的 `review_round_context.json` 为 `incremental`，增量 diff 只包含第 4 次提交的变化。

## 第 1 轮

建立独立的验收文件，作为后续轮次完整 PR diff 的稳定基线。

## 第 2 轮

第 1 轮的 [AI PR Review 运行](https://github.com/Terry-Mao/AICodingFlow/actions/runs/40540156835) 成功发布了 1 条 Bot Review；其产物记录 `round: 1`、`mode: full`。
在同一 base/head 快照上执行的[手动重跑](https://github.com/Terry-Mao/AICodingFlow/actions/runs/40540467072)跳过了 review job，Bot Review 总数仍为 1。

本次只增加上述验收记录，检查第 2 轮是否继续读取从 base 到当前 head 的完整 PR diff。

## 第 3 轮

第 2 轮的 [AI PR Review 运行](https://github.com/Terry-Mao/AICodingFlow/actions/runs/40540618294) 成功发布了第 2 条 Bot Review；产物记录 `round: 2`、`mode: full`，其 `pr_diff.txt` 同时包含第 1 轮与第 2 轮的内容。

本次追加新的验收记录，检查第 3 轮是否仍采用完整 PR diff。
