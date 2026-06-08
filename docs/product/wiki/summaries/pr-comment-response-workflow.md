---
type: summary
title: PR comment response workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-02
review_due: 2026-08-31
sources:
  - docs/product/raw/pr-comment-response-workflow.md
---

# PR comment response workflow 摘要

Source: [docs/product/raw/pr-comment-response-workflow.md](../../raw/pr-comment-response-workflow.md)

`respond-to-pr-comment` workflow 响应 PR 中显式 `@AGENT_LOGIN /fix` 请求，让 Codex agent 基于当前 PR 上下文产出修复 diff，并由外层 GitHub Actions 提交、推送、更新原 PR 或创建 follow-up PR。

## 触发条件

- PR conversation comment：`issue_comment.created` 且 issue 是 PR，`trigger_kind = conversation`。
- PR inline review comment：`pull_request_review_comment.created`，`trigger_kind = review`。
- PR review body：`pull_request_review.submitted` 或 `pull_request_review.edited`，`trigger_kind = review_body`。
- 触发命令必须在可见正文行中以完整 `@AGENT_LOGIN /fix` command 开头，同一行可追加修复说明。
- 引用块、fenced code block、部分用户名匹配、普通 mention、`/review` 或 `/implement` 不触发。
- 普通 issue comment 不属于该入口。
- `OWNER`、`MEMBER` 或 `COLLABORATOR` 触发者会继续运行 agent 和写权限步骤。
- 私有仓库中 `author_association = CONTRIBUTOR` 的触发者还需要实时 collaborator permission 查询确认其对仓库具有 `write`、`maintain` 或 `admin` 权限；满足时也视为授权。

## 上下文与分支策略

- `prepare_pr_comment_context.py` 生成 `pr_comment_context.json`、PR diff、可用 spec context 和 inline review comment id 索引。
- PR body、comments、review bodies、review comments 和 trigger comment body 都是任务数据，不能覆盖 workflow 规则、skill 规则、输出路径、分支策略或安全边界。
- agent 使用 workflow 提供的稳定本地 JSON 和 snapshot 文件作为 PR discussion context，不额外 fetch GitHub context。
- agent 不直接调用 GitHub API、创建 PR、发布评论、resolve thread、commit 或 push。
- `push-head`：触发者已授权且 workflow token 能写 PR head branch，修复提交到原 PR head branch。
- `fallback-pr-to-fork`：不能写原 PR head branch 但可写 base repo 时，基于原 PR head commit 创建 fallback branch 并创建或更新 follow-up PR。
- `blocked`：既不能写 head branch 也不能写 fallback branch 时，不运行 agent 修改代码。

## Agent 输出与外层处理

- agent 做最小合理修改；没有值得提交的 diff 时，workflow 不创建空提交或 follow-up PR。
- 有可提交 diff 时，agent 必须把 `implementation_summary.md` 和 `pr-metadata.json` 写到 `pr-worktree/.codex-runtime/handoff/`。
- `pr-metadata.json` 至少包含 `branch_name`、`pr_title`、`pr_summary` 和 `intended_files`；`branch_name` 必须等于 context 允许的 `agent_push_branch`。
- `intended_files` 必须覆盖所有应提交文件，不能包含 handoff、日志或缓存文件。
- agent 可在确实解决 inline review comments 时把 `resolved_review_comments.json` 写到同一个 `pr-worktree/.codex-runtime/handoff/` 目录，其中 comment id 必须来自当前 PR 真实 inline review comment id。
- 外层 workflow 校验 metadata、resolved comments 和实际 diff 后提交并 push 到允许 branch。
- PR discussion context、diff snapshot、spec context、metadata、summary 和 validation logs 位于 `pr-worktree/.codex-runtime/handoff/`，workflow 排除 `.codex-runtime/`，不污染提交内容。
- `push-head` 成功后不会按 metadata 改写原 PR title/body；fallback PR 会在 PR body 中说明来源 PR 和触发评论。
- resolve review thread 失败只记录 warning，不回滚已完成的 commit、push 或 PR update。
- 修改 `.github/workflows/` 下 GitHub workflow 文件时，外层 workflow 会通过 GitHub App installation token 设置 `WORKFLOW_UPDATE_TOKEN`；仓库需要配置 `APP_CLIENT_ID` Actions variable 和 `APP_PRIVATE_KEY` Actions secret。

## 支持的概念

- [PR comment response workflow](../concepts/pr-comment-response-workflow.md)
- [PR comment response 分支策略](../concepts/pr-comment-response-branch-strategy.md)
- [Agent 与外层 workflow 职责边界](../concepts/agent-workflow-boundaries.md)
