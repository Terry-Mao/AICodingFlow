# PR Review 跨轮次线上验收

此文件只用于 [#295](https://github.com/Terry-Mao/AICodingFlow/issues/295) 的临时测试 PR，完成验收后关闭 PR，不合并到 `main`。

## 验收目标

1. 同一 base/head 快照重复触发时，不新增 Bot Review。
2. 第 1 至第 3 轮的 `review_round_context.json` 均为 `full`。
3. 第 4 轮的 `review_round_context.json` 为 `incremental`，增量 diff 只包含第 4 次提交的变化。

## 第 1 轮

建立独立的验收文件，作为后续轮次完整 PR diff 的稳定基线。
