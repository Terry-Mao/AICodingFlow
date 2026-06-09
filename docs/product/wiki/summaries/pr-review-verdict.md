---
type: summary
title: PR review verdict 与 non-member gate 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-09
review_due: 2026-09-07
sources:
  - docs/product/raw/pr-review-verdict.md
---

# PR review verdict 与 non-member gate 摘要

Source: [docs/product/raw/pr-review-verdict.md](../../raw/pr-review-verdict.md)

自动 PR review 将 `review-pr` / `review-spec` 产出的机器评审结论写入 `review.json.verdict`，发布流程再把该结论映射为 GitHub review event。`verdict` 是 Bot 的机器判断，不直接等同于 GitHub 的最终 merge gate。

## Review 输出契约

- `review.json` 必须包含 `verdict`、`body` 和 `comments`。
- `verdict` 只能是 `APPROVE` 或 `REJECT`。
- `APPROVE` 表示没有阻塞级发现。
- `REJECT` 表示存在需要修复后再合并的阻塞级发现。
- 建议和 nit 不应单独导致 `REJECT`。
- `recommended_reviewers` 仅用于需要推荐人工 reviewer 的场景，必须是字符串数组，最多包含 1 个 reviewer。

## 触发与 skill 选择

- AI PR Review 默认由目标项目 CI 成功路径通过 `workflow_dispatch` 输入 PR number 触发；AICodingFlow 参考 `CI` workflow 在非 draft、同仓库 head PR 的测试和编译检查成功后 dispatch `review-pr.yml`。
- 目标项目已有自己的 CI 时，应在自己的 CI 成功路径中 dispatch `review-pr.yml`，而不是修改已安装的 `review-pr.yml`。
- AI PR Review 也可以手动通过 `workflow_dispatch` 输入 PR number 触发，或由 open 且非 draft PR conversation comment 中的 `@AGENT_LOGIN /review` body-level command 从 `issue_comment` 事件触发。
- `review-pr.yml` 不直接监听 GitHub `pull_request` 事件。
- `workflow_dispatch` 触发允许 `github-actions[bot]` 运行 Codex review action；如果目标仓库改用 GitHub App token、PAT 或第三方 CI dispatch，需要让 bot allowlist 与实际触发 actor 匹配，或改用有人类账号权限的 token 触发。
- 手动触发和 comment 触发会先解析目标 PR，再复用 review 流程。
- Comment 触发要求 `@AGENT_LOGIN /review` 独占一行，允许前后空白。
- 裸 `/review`、单纯 `@AGENT_LOGIN` mention、quoted line、fenced code block、普通句子中的提及，以及带额外参数的 `@AGENT_LOGIN /review ...` 都不会触发 AI review。
- 普通 issue comment 和 PR inline review comment 不是 comment 触发入口。
- 只有 open、非 draft 且 head repository 与当前仓库一致的 PR 会继续进入 AI review。
- closed PR、draft PR 或来自 fork 的 PR 会被跳过，不会运行 agent、发布 review 或上传 review artifact。
- spec-only PR 使用 `review-spec-repo`；其他 code PR 使用 `review-pr-repo`。
- 仓库本地 wrapper skill 补充本仓库评审偏好，不改变核心输出契约。

## Comment / manual 触发状态

- PR comment 或 `workflow_dispatch` 触发 AI PR Review，且目标 PR 的 head repository 是当前仓库时，workflow 会在 PR head commit 上写入 `AI PR Review` commit status。
- Review 开始时 status 为 `pending`，结束后按 job 结果更新为 `success` 或 `failure`，target URL 指向对应 GitHub Actions run。
- 该 status 让 CI dispatch、comment 或手动触发的 review run 出现在目标 PR 的 checks / statuses 视图中。
- AICodingFlow 参考 `CI` workflow 不再在测试前预写 `AI PR Review` status；测试失败、测试被跳过或 dispatch 未发生时，参考 `CI` workflow 不写入该 status。
- 来自 fork 的 PR 不会写入该 status。

## 安全补充 review

- Code PR review 会在基础 `review-pr` 之外应用 `security-review-pr`。
- Spec-only PR review 会在基础 `review-spec` 之外应用 `security-review-spec`。
- 安全发现合并进同一个 `review.json`，不会生成单独输出。
- 安全补充只报告有证据的问题，不运行动态扫描，不查询外部安全 API，不制造理论风险，也不直接发布 GitHub comment。
- 安全发现的 review comment 使用 `[SECURITY]` 标签，并计入同一个 `review.json.verdict`；critical security finding 通常应导致 `REJECT`。

## PR 作者与类型

- `COLLABORATOR`、`MEMBER`、`OWNER` 视为 member / collaborator / owner。
- 其他非空、可识别身份在作者不是 bot 或 automation user 时视为 non-member。
- bot / automation user 不视为 non-member。
- `author_association` 缺失、为空或异常时采用保守行为，不视为 non-member。
- changed files 不全在 `specs/` 下时为 code PR。
- changed files 非空且全部路径以 `specs/` 开头时为 spec-only PR。
- spec-only PR 不进入 non-member blocking 或 reviewer request flow。

## Event 映射与 reviewer

- 只有 `non-member code PR + verdict = REJECT` 会发布 GitHub `REQUEST_CHANGES`。
- 其他场景默认发布 `COMMENT`。
- `non-member code PR + verdict = APPROVE` 时，workflow 尝试从 `.github/CODEOWNERS` 请求 1 个 human reviewer。
- 推荐 reviewer 必须是字符串、最多 1 个、不能是 PR 作者本人，并且必须出现在 `.github/CODEOWNERS`。
- 没有合格推荐时，workflow 使用 CODEOWNERS fallback。
- 没有可用 CODEOWNERS owner 时，不请求 reviewer，但 Bot review 发布仍可完成。

## Merge gate 语义

最终能否 merge 由 GitHub branch protection、required checks、code owner review、blocking `REQUEST_CHANGES` 和维护者权限共同决定。

## 本地 review 入口

- 本地开发完成但尚未 push 或创建 PR 时，可以使用 `review-pr-local` 或 `review-spec-local`。
- 两个本地 skill 会先准备根目录快照，再分别委托给 `review-pr-repo` 或 `review-spec-repo`。
- 本地 review 输入与输出固定在仓库根目录：`pr_description.txt`、`pr_diff.txt`、按需生成的 `spec_context.md`、`.local_review_baseline.status` 和 `review.json`。
- 准备阶段支持 worktree 中已有 staged、unstaged 和未跟踪文件改动。
- `pr_diff.txt` 始终基于当前 worktree 相对选定 base 的完整状态生成；未被 Git ignore 的未跟踪文件会纳入 diff。
- `.local_review_baseline.status` 记录准备阶段完成后的业务文件 dirty 状态，并被 Git ignore。
- review 阶段只能写入受控 review 输出文件；校验会允许 baseline 中已存在的业务文件状态继续存在，但拒绝新增业务文件改动、业务文件状态变化、staged 输出、非 review 快照文件变更，以及 review 输出被意外删除。
- 本地 review 的 base 可以显式传入；未显式传入时，已有 GitHub PR 的当前分支优先使用该 PR 的 base SHA，没有可用 PR base SHA 时按 `origin/main`、`upstream/main`、`main` 解析。
- code review 根据本地 diff 中的 changed files 解析 spec context；spec-only review 不生成 spec context。

## 支持的概念

- [AI PR Review workflow](../concepts/ai-pr-review-workflow.md)
- [Comment / manual review status](../concepts/comment-manual-review-status.md)
- [安全补充 review](../concepts/security-review-supplements.md)
- [PR review verdict](../concepts/pr-review-verdict.md)
- [Non-member gate 与 reviewer 请求](../concepts/non-member-gate-and-reviewer-request.md)
- [本地 PR review 入口](../concepts/local-pr-review-entrypoints.md)
