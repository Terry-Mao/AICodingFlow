# 技术规格：PR 审查流程一期

## Problem

一期对应 [产品规格](product.md)。基线提交 `e767f582fd227910160d3a57cd0e699be56d82a1` 上，`.github/workflows/review-pr.yml` 每次运行只读取当前 PR diff 与讨论快照，`.github/scripts/post_pr_review.py` 不记录可复用的审查轮次，自动 PR 元数据仅要求摘要。

## Relevant code

- `.github/workflows/review-pr.yml:116`：准备快照、调用 Codex、校验并发布 Review。
- `.github/scripts/post_pr_review.py:471`：把 `review.json` 发布为 GitHub Review。
- `.github/scripts/prepare_review_discussion_context.py:93`：旧意见的去重上下文。
- `.github/scripts/validate_implementation_output.py:28` 与 `validate_spec_output.py:26`：自动 PR 元数据校验。
- `.github/workflows/ci.yml:5`：PR 必需检查入口。

## Proposed changes

1. PR 模板与共享正文校验器统一四个章节；本地 `create-pr` 在提交前运行校验，自动实现、spec 与 PR comment 元数据校验调用同一规则。CI 的 `pr-body` job 对所有 PR 校验正文；其他自动化 PR 使用共享补全器补齐章节。
2. `prepare_review_round_context.py` 查询已发布的 Bot Review，按不同 `commit_id` 计数。新发布 Review 的 body 附带 base/head SHA 标记，以支持下一次运行判断 base 是否仍相同；旧 Review 缺标记时安全回退完整审查。
3. preflight 在调用 Codex 前跳过同一 head 的既有 Bot Review，并在重跑时恢复该 head 的 `AI PR Review` 状态。第四轮起，仅当先前 head 是当前 head 的祖先且 base SHA 与上轮一致时，生成增量 `PR_DIFF_V1`。当前完整 PR diff 继续用于合法 inline 定位。发布前再次确认 PR head/base 快照未改变；没有内容的 `REJECT` 不得发布。
4. `ci.yml` 监听 `merge_group` 并运行同一测试任务；PR 正文编辑后，非草稿 PR 重新运行测试，通过正文校验后分发 AI PR Review。AI PR Review 只在 `pull_request` 事件分发。此变更仅为未来队列准备检查，不启用队列。

## Testing and validation

- 单测验证不同 SHA 计数、同 SHA 重跑、base 变化与历史改写回退、发布时过期快照及重复 Review 抑制。
- 单测验证 PR 正文章节与不同入口的校验行为。
- 运行仓库完整单测、Python 编译检查、`actionlint`、`git diff --check`。

## Risks and mitigations

- GitHub 旧 Review 没有 base 标记：仅使用完整审查，不猜测增量。

## Follow-ups

二期评估 2 个独立发现 Agent 加 1 个验证 Agent 的共识，以及低／中／高风险真人审批检查。夜间存量扫描待产品规则明确后另行设计。三期在符合条件的组织仓库启用 merge queue。
