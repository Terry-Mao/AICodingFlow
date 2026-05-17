# 产品规格：增加 `respond-to-pr-comment` workflow

## 1. Summary

新增一个 GitHub Actions workflow，用于响应 PR 中的显式 `@bot /fix` 评论，让 Codex agent 在当前 PR 上产出修复 diff，并由外层 workflow 提交、推送、更新 PR 或创建 follow-up PR。该 workflow 面向 PR conversation comment、inline review comment、以及 PR review body，不是 issue 的 `ready-to-spec` 或 `ready-to-implement` 流程。

期望结果是：`review-pr` 或人工 reviewer 在 PR 上留下问题后，维护者可以在相关评论位置使用 `@bot /fix ...` 触发 Bot 修复。Bot 应读取稳定的 PR 评论上下文、PR diff、可用 spec context 和分支权限信息；agent 负责修改代码或文档并写出 handoff artifacts；外层 workflow 负责安全地提交、推送、更新 PR、创建 fallback follow-up PR、回复已解决的 inline review comment，并尝试 resolve review thread。

## 2. Problem

当前仓库已经有 `review-pr` 自动评审 workflow，也有从 issue 创建 specs 和 implementation PR 的 workflow，但缺少“PR 评论驱动的修改当前 PR”能力。当 `review-pr` 或人工 reviewer 提出问题后，维护者只能手动让 agent 在本地或另一个实现流程里修复，难以稳定关联触发评论、PR head branch、分支权限、review thread 和后续 PR 更新。

该功能解决的用户问题包括：

- 维护者希望在 PR review comment 下直接回复 `@bot /fix`，让 Bot 修改该 PR，而不是重新走 issue implementation。
- reviewer 希望 Bot 修复后能在对应 inline review comment 下回复，并在确实解决时尝试 resolve thread。
- workflow 需要根据 PR head branch 权限决定直接 push、fallback 到 base repo branch，或明确 blocked。
- agent 需要稳定结构化的 PR 评论上下文，避免把 PR body、comments、review comments 或 trigger comment 当作高权限指令。
- 外层 workflow 需要验证 agent 输出，避免 agent 直接调用 GitHub API、随意 push 到错误分支或伪造已解决 comment。

## 3. Goals

- 新增 `respond-to-pr-comment` workflow，处理 PR 评论中的显式 `@bot /fix` 请求。
- 支持三类触发来源：
  - PR conversation comment：`issue_comment.created` 且 `issue` 是 PR，`trigger_kind = conversation`。
  - PR inline review comment：`pull_request_review_comment.created`，`trigger_kind = review`。
  - PR review body：`pull_request_review.submitted` 或 `pull_request_review.edited`，`trigger_kind = review_body`。
- 只在评论正文中存在可见、未引用、未在 fenced code block 内的 `@<AGENT_LOGIN> /fix` 指令时运行；该指令可以独占一行，也可以在同一行追加修复说明。
- 只允许 `OWNER`、`MEMBER`、`COLLABORATOR` 触发写权限流程；其他 `author_association` 必须 `should_run=false`，不得运行 agent、checkout PR head、commit、push 或 apply。
- 生成稳定的 `pr_comment_context.json`，包含 PR、trigger、触发者授权状态、分支策略、spec context、coauthor directives 和 agent push 目标。
- 支持三种分支策略：
  - `push-head`：直接提交并 push 到 PR head branch。
  - `fallback-pr-to-fork`：无法修改原 PR head 时，基于原 PR head commit 在 base repo 创建 fallback branch，并由外层 workflow 创建或更新 follow-up PR。
  - `blocked`：无可用写入路径时，不运行 agent 修改代码，只在 workflow 输出中说明无法处理。
- agent 必须使用实现类 skills：`implement-issue`、`implement-specs`、`spec-driven-implementation`，并把 PR 内容作为数据分析。
- agent 可以修改当前 PR 范围内的代码、测试、docs、specs 或 workflow 文件，但不得自行 commit、push、创建 PR、调用 GitHub API 或 resolve comments。
- agent 必须在有修改时写出 `pr-metadata.json`；当本次确实解决 inline review comments 时，可以写出 `resolved_review_comments.json`。
- 外层 workflow 必须验证 `pr-metadata.json`、`resolved_review_comments.json` 和实际 diff，再负责 commit、push、PR update/follow-up PR、review comment reply 和 thread resolve。
- 支持上传调试 artifacts，包括 context、metadata、resolved comments、summary 和 validation logs。

## 4. Non-goals

- 不替代 `create-spec-from-issue`、`create-implementation-from-issue` 或 issue label 驱动流程。
- 不响应普通 issue comments；只有 PR 相关 comments/reviews 能触发。
- 不把 `/fix` 作为聊天回复流程；该 workflow 的结果是 PR 分支修改或明确 no-op/blocked 状态。
- 不让 agent 直接调用 GitHub API、直接发布评论、直接 resolve review thread、直接 push branch 或创建 PR。
- 不自动 merge PR。
- 不要求所有 `@bot /fix` 都一定产生 diff；当请求不清楚、不可执行或无必要修改时可以 no-op。
- 不允许普通 PR conversation comment 被伪造成 inline review comment resolution；只有真实 PR review comment id 可以进入 `resolved_review_comments.json`。
- 不支持未授权外部贡献者通过 `@bot /fix` 触发写权限流程；这类请求只产生明确 skip/blocked 结果。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub Actions、agent prompt、workflow handoff 和评论处理行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### 触发行为

- 用户在 PR conversation、PR inline review comment 或 PR review body 中写入 `@bot /fix` 才能触发。
- `@bot /fix` 必须出现在可见正文行中；引用块、fenced code block、部分用户名匹配、`/review`、`/implement` 或普通 mention 都不触发。
- workflow 必须识别触发来源并记录：
  - `trigger_kind`
  - `trigger_comment_id`
  - `review_reply_target_id`
  - `trigger_actor`
  - `trigger_actor_association`
  - `trigger_actor_is_authorized`
  - `should_run`
  - `skip_reason`
- 触发者授权是硬门禁，不只是上下文字段。只有 `author_association` 为 `OWNER`、`MEMBER`、`COLLABORATOR` 时才允许 `should_run = true`。
- 对于 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR`、`FIRST_TIMER`、`MANNEQUIN`、`NONE`、空值或未知值，workflow 必须设置 `should_run = false` 和明确 `skip_reason`，并跳过所有 agent 和写入步骤。
- 对于 inline review comment 触发，`review_reply_target_id` 应指向该 review comment，方便外层 workflow 后续回复原评论。
- 对于 conversation 或 review body 触发，workflow 可以回复触发位置或 PR conversation，但不得把其 id 放入 `resolved_review_comments.json`。
- PR body、comments、review comments、triggering comment body 只作为数据，不能覆盖 workflow 规则、skill 规则、输出路径、分支策略或安全边界。

### 分支策略体验

- 同仓库 PR 且 workflow token 能写 head branch 时，使用 `push-head`。
- fork PR 且 `maintainer_can_modify = true` 且 workflow 能写 head branch 时，可以使用 `push-head`。
- fork PR 或其他场景无法写 head branch，但 base repo 可写时，使用 `fallback-pr-to-fork`。
- fallback branch 命名默认使用 `spec/respond-pr-<pr_number>`，可以在需要避免冲突时追加短 slug，但必须保持可验证前缀。
- 当触发者未授权时设置 `should_run = false`；当触发者已授权但既不能修改 head branch、也不能写 fallback branch 时，使用 `blocked`。两种场景都不运行 agent 修改代码，并输出用户可理解的原因。
- branch strategy、agent push repo、agent push branch 必须写入 `pr_comment_context.json`，agent 只能把 metadata 指向允许的目标。

### agent 执行行为

- workflow 在运行 agent 前必须 checkout 正确实现基线：
  - `push-head`：checkout PR head commit/branch。
  - `fallback-pr-to-fork`：基于 PR head commit 创建 fallback branch 工作区。
- agent 应读取 `pr_comment_context.json`、PR diff 快照、可用 `spec_context.md`，并按 prompt 指定顺序读取 `implement-issue`、`implement-specs`、`spec-driven-implementation`。
- agent 应使用仓库提供的 `fetch_github_context.py` 获取额外 PR 内容；不得通过其他 GitHub API 或 live fetch 绕过稳定上下文。
- agent 根据触发评论、相关 review discussion、PR diff 和 spec context 判断应修改什么。
- 如果请求与现有 spec context 冲突，agent 应做最小合理修改，并在 summary 中说明假设或冲突；不得让评论静默覆盖 approved specs。
- 如果没有值得修改的 diff，agent 应写出 summary 或保持无实现 diff，外层 workflow 不应创建空提交。
- 如果修改改变 PR 范围或标题/正文应更新，agent 必须写出 `pr-metadata.json`。
- `pr-metadata.json` 至少包含：
  - `branch_name`：必须等于允许 push 的 branch。
  - `pr_title`：conventional commit style，反映实际修改。
  - `pr_summary`：完整 markdown PR body。对于 fallback follow-up PR，应引用原 PR；对于原 PR 更新，应保留或更新相关 issue reference。
  - `intended_files`：应提交的 repository-relative 文件列表。
- 如果解决了 inline review comments，agent 可以写出 `resolved_review_comments.json`：

```json
{
  "resolved_review_comments": [
    {
      "comment_id": 123456789,
      "summary": "Updated `core/webhook.py` to validate the GitHub signature before parsing the payload."
    }
  ]
}
```

- `comment_id` 必须来自 fetched PR context 中的 `pr-review-comment` numeric id。
- 只有本次修改实际解决的 inline review comments 才能列入 resolved list。
- 没有解决任何 inline review comment 时，不应上传 `resolved_review_comments.json`。

### 外层 workflow 结果行为

- agent 运行后，workflow 必须检查是否有非临时 diff。
- 无 diff 时，不提交、不 push、不创建 follow-up PR，并在触发位置或 progress 输出中说明已分析但没有产生修改。
- 有 diff 时，workflow 校验 metadata、提交 intended files、push 到 branch strategy 允许的目标。
- `push-head` 成功后，workflow 更新原 PR title/body，当 `pr-metadata.json` 存在且有效时使用其内容。
- `fallback-pr-to-fork` 成功后，workflow 查找或创建 base repo 中从 fallback branch 指向原 PR 的 follow-up PR，并在 PR body 中说明来源 PR 和触发评论。
- 如果有 `resolved_review_comments.json`，workflow 对每个 comment：
  - 回复原 review comment，说明本次修改如何处理。
  - 尝试通过 GraphQL `resolveReviewThread` resolve 对应 thread。
  - resolve 失败不应回滚已经 push 的修复，但必须在日志中可见。
- workflow 不得伪造 resolved comments，不得 resolve 普通 PR conversation comment。

## 7. Success criteria

- PR conversation comment 中可见的 `@bot /fix` 会触发 `trigger_kind = conversation`。
- PR inline review comment 中可见的 `@bot /fix` 会触发 `trigger_kind = review`，并记录可回复的 review comment id。
- PR review body 中可见的 `@bot /fix` 会触发 `trigger_kind = review_body`。
- 引用块、fenced code block、普通 issue comment、无 `/fix` 的 mention、部分用户名匹配都不会触发。
- workflow 产出的 `pr_comment_context.json` 包含 PR number、head/base repo、head/base branch、branch strategy、trigger metadata、spec context 状态和 coauthor directives。
- `OWNER`、`MEMBER`、`COLLABORATOR` 以外的触发者不会运行 agent，也不会执行任何需要 `contents`、`pull-requests` 或 `issues` write 权限的修改步骤。
- `push-head` 场景会把修复提交到 PR head branch，不创建 follow-up PR。
- `fallback-pr-to-fork` 场景会把修复提交到 `spec/respond-pr-<pr_number>` 前缀分支，并创建或更新 follow-up PR。
- `blocked` 场景不会运行 agent 修改代码，不会 push，并给出明确原因。
- agent prompt 明确要求 GitHub 内容作为数据，不作为系统指令。
- `pr-metadata.json.branch_name` 只能指向 branch strategy 允许的 branch。
- `resolved_review_comments.json` 只接受真实 PR review comment id，拒绝普通 conversation comment id、缺失 id、重复 id 或非本 PR id。
- 外层 workflow 会在实际解决 inline review comment 后回复并尝试 resolve thread。
- 无实现 diff 时不会创建空提交、不会创建 follow-up PR。
- 需要 workflow file 写权限的修改遵循现有 `WORKFLOW_UPDATE_TOKEN` 保护模式。

## 8. Validation

- 增加触发解析单元测试，覆盖三类 event、`@bot /fix` 精确匹配、引用块和 fenced code block。
- 增加触发者授权测试，覆盖 `OWNER`、`MEMBER`、`COLLABORATOR` 允许运行，以及 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR`、`FIRST_TIMER`、`NONE`、空值或未知值必须 `should_run=false`。
- 增加 `PrCommentContext` 生成测试，覆盖同仓库 PR、可修改 fork PR、不可修改 fork PR、blocked 权限场景。
- 增加 branch strategy validation 测试，确认 `pr-metadata.json.branch_name` 不能越过允许 branch。
- 增加 `resolved_review_comments.json` validation 测试，确认只接受 fetched PR review comment ids。
- 增加外层 apply/finalize 测试，覆盖 no diff、push-head、fallback follow-up PR、metadata update、resolved comments reply 和 thread resolve failure。
- 增加 prompt/static tests，确认 workflow 不把 PR body/comments inline 到高权限 prompt 中，而是通过稳定 context 和 fetch helper 传递。
- 手动或 dry-run 验证一个 `review-pr` inline comment 下的 `@bot /fix` 能产生 commit、回复原 comment，并在可行时 resolve thread。

## 9. Decisions

- `@bot /fix` 允许在同一可见行中追加修复说明，但必须以完整 `@<AGENT_LOGIN> /fix` command 开头；引用块、fenced code block、部分用户名匹配和普通 mention 都不触发。
- fallback branch 必须基于原 PR head commit 创建，避免 follow-up PR 脱离待修 PR 的实际代码状态。
- review body 触发时，agent 只处理 review body 和相关讨论中明确要求的修复；不得默认扩大到整次 review 的所有 comments。
- thread resolve 失败只记录 warning 和可见日志，不回滚已经完成的 commit/push/PR update。
- v1 不引入 trusted organization membership 查询；授权只基于 GitHub `author_association` 的 `OWNER`、`MEMBER`、`COLLABORATOR`。
