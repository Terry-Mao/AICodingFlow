# 产品规格：PR Bot `/review` 指令

## 1. Summary

本功能为 PR 下的 Bot 增加 `/review` 指令，让维护者可以在 PR body-level comment 中通过 `@AGENT_LOGIN /review` 显式重新触发现有 `review-pr` / `review-spec` workflow。目标是把“重新运行 AI PR Review”从单纯 mention Bot 或手动 workflow dispatch，收敛成一个清晰、可审计、可测试的 PR Bot 评论命令。

期望结果是：当用户在非 draft PR 的普通 PR 评论中发送 `@AGENT_LOGIN /review` 时，AI PR Review workflow 会重新运行，并继续按现有规则选择 `review-pr-repo` 或 `review-spec-repo`。draft PR、非 PR issue 评论、inline review comment、缺少 Bot mention 的裸 `/review`、quoted text 或包含命令但不是 body-level command 的内容不应触发 review。

## 2. Problem

当前 AI PR Review 已支持 PR 事件自动运行，也支持 PR comment mention `@AGENT_LOGIN` 和手动 `workflow_dispatch`。但重新触发 review 的用户体验不够直接：维护者需要知道 Bot login，或者进入 Actions 手动触发并填写 PR number。

这会带来几个问题：

- 重新触发 review 的入口不够符合常见 GitHub Bot 指令习惯。
- 单纯 `@AGENT_LOGIN` mention 容易和普通讨论混在一起；`@AGENT_LOGIN /review` 可以同时表达目标 Bot 和具体动作。
- issue 正文要求 `/review` 必须作为发送给 Bot 的 body-level command，并且 PR 必须是非 draft 状态；现有 mention 触发逻辑没有表达这些边界。

## 3. Goals

- 在 PR body-level comment 中支持 `@AGENT_LOGIN /review` 指令。
- `@AGENT_LOGIN /review` 只对 open 且非 draft 的 PR 生效。
- `@AGENT_LOGIN /review` 只从普通 PR conversation comment 触发，不从 inline review comment 或普通 issue comment 触发。
- `/review` 必须作为发给 Bot 的 body-level command 出现，不能来自 quoted text、代码块、inline diff 评论、缺少 Bot mention 的裸命令或普通段落中的随意提及。
- Bot `/review` 触发后复用现有 AI PR Review workflow，不引入新的 review 逻辑。
- 触发后的 review skill 选择保持现状：纯 `specs/` PR 使用 `review-spec-repo`，其他 PR 使用 `review-pr-repo`。
- 继续保留 `workflow_dispatch` 和 PR event 自动触发能力。
- 对跳过场景给出可理解的 skip 行为，避免 draft PR 或非 PR issue 误触发 review。

## 4. Non-goals

- 不实现 feature 或修改生产代码；本 PR 仅创建规格。
- 不新增 `/spec`、`/implement`、`/approve` 等其他 Bot 指令。
- 不改变 `review-pr` / `review-spec` 的评审标准、`review.json` 契约或发布规则。
- 不改变 PR `opened` / `reopened` / `synchronize` / `ready_for_review` 的自动触发行为。
- 不要求 `/review` 支持普通 issue。
- 不要求从 GitHub review inline comment 或 review thread 中触发。
- 不引入权限模型以区分维护者、贡献者或外部用户；如需限制谁能触发，应另开任务设计。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub Actions 与 PR comment command 行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### 触发入口

- 用户在 PR 的 conversation timeline 中创建普通 comment。
- comment body 的 body-level command 为 `@AGENT_LOGIN /review`，其中 `AGENT_LOGIN` 来自 workflow 配置的 Bot login。
- PR 必须是 open 且非 draft。
- 触发后运行现有 `.github/workflows/review-pr.yml`，并对该 PR 重新生成 `pr_description.txt`、`pr_diff.txt`、按需生成 `spec_context.md`、运行 Codex review、校验并发布 GitHub PR review。

### Body-level command 规则

`@AGENT_LOGIN /review` 应被视为发给 Bot 的 body-level command，而不是任意子串匹配：

- 单独一行 `@AGENT_LOGIN /review` 必须触发。
- `@AGENT_LOGIN /review` 行前后允许空白行。
- ` @AGENT_LOGIN /review ` 这类仅带前后空白的行应触发。
- 单独一行裸 `/review` 不触发。
- quoted line 中的 `> @AGENT_LOGIN /review` 不触发。
- fenced code block 中的 `@AGENT_LOGIN /review` 不触发。
- 普通句子中的 `please @AGENT_LOGIN /review this` 不触发。
- 其他命令或额外参数，例如 `@AGENT_LOGIN /review now`，不属于本次必须支持范围，默认不触发。
- 同一 comment 中只要存在一个有效 body-level `@AGENT_LOGIN /review` command，就可以触发一次 review。

### Draft 与 PR 状态

- 对 draft PR，`@AGENT_LOGIN /review` 不应启动 AI review job。
- 对 closed PR，`@AGENT_LOGIN /review` 不应启动 AI review job。
- 对 open 且非 draft 的 same-repo PR，`@AGENT_LOGIN /review` 可以触发 review。
- 对 fork PR，应沿用现有 `review-pr.yml` 的安全边界；如果 workflow 当前不会安全地 checkout 或发布 fork PR review，`@AGENT_LOGIN /review` 不应放宽该限制。

### 与现有触发方式的关系

- PR 自动触发保持不变：非 draft PR 在 `opened`、`reopened`、`synchronize`、`ready_for_review` 时仍自动运行。
- `workflow_dispatch` 保持不变，可继续通过 PR number 手动触发。
- 现有单纯 `@AGENT_LOGIN` comment mention 不应继续作为 review 触发入口；必须显式使用 `@AGENT_LOGIN /review`。
- `@AGENT_LOGIN /review` 触发后不需要用户指定 review 类型；workflow 继续根据 changed files 自动选择 `review-pr-repo` 或 `review-spec-repo`。

### 跳过体验

- 普通 issue comment 中的 `@AGENT_LOGIN /review` 不触发 PR review。
- PR inline review comment 或 review thread 中的 `@AGENT_LOGIN /review` 不作为本功能入口。
- 无效 `@AGENT_LOGIN /review` comment 不应创建无意义的 review output，也不应让 review job 进入半执行状态。
- 如果跳过，workflow 日志应能说明原因，例如不是 PR comment、PR 是 draft、PR 已关闭或 comment 不包含有效 body-level Bot `/review` command。

## 7. Success criteria

- 在 open 且非 draft PR 的普通 body-level comment 中发送单行 `@AGENT_LOGIN /review`，会重新触发 AI PR Review workflow。
- `@AGENT_LOGIN /review` 触发后，workflow 使用目标 PR 的最新 PR payload，并按现有流程 checkout PR head、生成快照、选择 skill、运行 review、校验 `review.json`、发布 PR review。
- 纯 `specs/` PR 由 `@AGENT_LOGIN /review` 触发时仍选择 `review-spec-repo`。
- 非纯 `specs/` PR 由 `@AGENT_LOGIN /review` 触发时仍选择 `review-pr-repo`。
- draft PR 上的 `@AGENT_LOGIN /review` 不启动 review job。
- closed PR 上的 `@AGENT_LOGIN /review` 不启动 review job。
- 普通 issue comment 中的 `@AGENT_LOGIN /review` 不启动 PR review。
- 裸 `/review`、quoted text、fenced code block、普通句子或带额外参数的 `@AGENT_LOGIN /review` 不触发。
- `workflow_dispatch` 和 PR event 自动触发仍可用。
- 相关 README 或 workflow 测试能体现 `@AGENT_LOGIN /review` 是重新触发 review 的正式方式。

## 8. Validation

- 增加或更新 workflow 解析测试，覆盖 `@AGENT_LOGIN /review` issue_comment trigger 存在且 PR comment 才可进入 preflight。
- 增加或更新 `resolve_pr_event.py` 或相关 helper 的单元测试，覆盖 open non-draft PR 可 review、draft PR 不可 review、closed PR 不可 review。
- 增加 body-level command parser 单元测试，覆盖带 Bot mention 的单行命令、裸 `/review`、空白、quoted text、fenced code block、普通句子、带参数命令。
- 增加 workflow YAML 测试，确认 `issue_comment` trigger 仍存在，且 job gate 使用 Bot mention 与 `/review` 粗筛，而不是单纯 Bot mention 子串。YAML 不需要完整解析 quoted text、fenced code block 或整行精确匹配；这些 body-level Bot command 语义必须由 Python parser 单元测试覆盖，并由 preflight 的 `reviewable` 输出作为最终判定。
- 人工检查 README 中关于“需要重新 review 时”的说明，确认描述 `@AGENT_LOGIN /review` 的使用方式和 draft 限制。

## 9. Open questions

- 是否要限制只有 member / collaborator / owner 可以执行 `/review`？issue 未提出权限限制，本规格暂不要求。
- Bot `/review` 是否应该接受额外参数，例如 `@AGENT_LOGIN /review spec` 或 `@AGENT_LOGIN /review full`？本规格不支持额外参数，避免和未来命令语法冲突。
