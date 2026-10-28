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

1. PR 模板与共享正文校验器统一四个章节；本地 `create-pr` 在提交前运行校验，自动实现、spec 与 PR comment 元数据校验调用同一规则，其他自动化 PR 使用共享补全器补齐章节。`ci.yml` 不设置 `pr-body` job；手工创建的 PR 依靠模板提示，CI 不强制校验正文。
2. `prepare_review_round_context.py` 查询已发布的 Bot Review，按不同 base/head SHA 快照计数。新发布 Review 的 body 附带 base/head SHA 标记；旧 Review 缺标记时安全回退完整审查，且不复用其未知 base 的审查结果。
3. preflight 在调用 Codex 前跳过相同 base/head SHA 快照的既有 Bot Review，并在重跑时恢复该 head 的 `AI PR Review` 状态。第四轮起，仅当先前 head 是当前 head 的祖先且 base SHA 与上轮一致时，生成从上次已审查 head 到当前 head 的增量 `PR_DIFF_V1`。前三轮使用当轮 base 到 head 的完整 PR diff；当前完整 PR diff 继续用于合法 inline 定位。发布前再次确认 PR head/base 快照未改变，并按相同快照检查重复发布；没有内容的 `REJECT` 不得发布。
4. `ci.yml` 在非草稿 PR 新建、重新打开、推送及标记为可审查时运行测试，也监听 `merge_group` 并运行同一测试任务；`edited` 不触发 CI。AI PR Review 由 `pull_request_target` 自动触发；使用 `GITHUB_TOKEN` 创建或更新 PR 的工作流显式调用 `workflow_dispatch`，CI 不额外分发审查，避免同一 PR 自动运行两次。手动触发与 PR 评论命令保留。此变更仅为未来队列准备检查，不启用队列。

## Testing and validation

- 单测验证不同 base/head 快照计数、相同快照重跑、base 变化与历史改写回退、发布时过期快照及重复 Review 抑制。
- 单测验证本地与自动化入口的 PR 正文章节校验，以及 CI 不处理正文编辑事件。
- 运行仓库完整单测、Python 编译检查、`actionlint`、`git diff --check`。

## Risks and mitigations

- GitHub 旧 Review 没有 base 标记：仅使用完整审查，不猜测增量。
- 手工 PR 可在正文缺少章节时进入审查或合并；PR 模板继续提示作者填写，审查者按需要求补充，CI 不将正文格式作为合并门槛。

## Follow-ups

二期评估 2 个独立发现 Agent 加 1 个验证 Agent 的共识，以及低／中／高风险真人审批检查。夜间存量扫描待产品规则明确后另行设计。三期在符合条件的组织仓库启用 merge queue。
