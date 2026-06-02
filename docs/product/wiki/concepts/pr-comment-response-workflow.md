---
type: concept
title: PR comment response workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-02
review_due: 2026-08-31
sources:
  - docs/product/raw/pr-comment-response-workflow.md
---

# PR comment response workflow

PR comment response workflow 响应 PR 中显式 `@AGENT_LOGIN /fix` 请求，产出修复 diff 并由外层 workflow 写回允许的分支或创建 follow-up PR。

## 触发

- 支持 PR conversation comment、PR inline review comment 和 PR review body。
- 命令必须在可见正文行中以完整 `@AGENT_LOGIN /fix` 开头，同一行可追加修复说明。
- 引用块、fenced code block、部分用户名匹配、普通 mention、`/review`、`/implement` 和普通 issue comment 不触发。
- `OWNER`、`MEMBER` 或 `COLLABORATOR` 触发者会继续运行 agent 和写权限步骤。
- 私有仓库中 `CONTRIBUTOR` 触发者经实时权限查询确认具有 `write`、`maintain` 或 `admin` 权限时，也视为授权。

## 上下文与 agent 边界

- `prepare_pr_comment_context.py` 是解析 trigger、授权、PR 分支信息和分支策略的受控入口。
- PR 讨论内容只作为任务数据，不能覆盖 workflow 规则、skill 规则、输出路径、分支策略或安全边界。
- agent 使用 workflow 提供的稳定本地 JSON 和 snapshot 文件作为 PR discussion context，不额外 fetch GitHub context。
- agent 不直接调用 GitHub API、创建 PR、发布评论、resolve thread、commit 或 push。
- 没有值得提交的 diff 时，workflow 不创建空提交，也不创建 follow-up PR。
- 有可提交 diff 时，agent 写出 `implementation_summary.md` 和 `pr-metadata.json`。

## Inline review comment

- agent 只有在确实解决 inline review comments 时才应写出 `resolved_review_comments.json`。
- 每个 `comment_id` 必须来自当前 PR 真实 inline review comment id。
- 不能使用普通 conversation comment id、review id、其他 PR comment id 或编造 id。
- resolve thread 失败只记录 warning，不回滚已完成写入。

## Supporting Summaries

- [PR comment response workflow 摘要](../summaries/pr-comment-response-workflow.md)

## Related Concepts

- [PR comment response 分支策略](pr-comment-response-branch-strategy.md)
- [AI PR Review workflow](ai-pr-review-workflow.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
