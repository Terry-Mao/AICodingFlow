# 产品规格：PR review verdict 与 non-member gate 行为

## 1. Summary

本功能让 `review-pr` / `review-spec` 产生的机器评审结果不仅能发布为普通 GitHub review comment，还能在特定高风险场景下转换为真正的 GitHub blocking review event。目标是让 Bot 的判断、GitHub 上展示的 review event、以及是否请求人工 reviewer 之间有清晰、可验证、一致的规则。

期望结果是：`review.json` 明确包含 `verdict`，当 non-member 的 code PR 被 Bot 判定为 `REJECT` 时发布 `REQUEST_CHANGES`；其他场景默认继续发布 `COMMENT`，避免 Bot 对成员 PR 或 spec-only PR 产生过强的 merge gate 影响。

## 2. Problem

当前 PR review 自动化会读取 `review.json` 并发布 GitHub PR review，但发布脚本固定使用 `COMMENT`。当 `review-pr` 或 `review-spec` 发现重要问题时，GitHub PR 页面没有明确的拒绝状态，维护者需要从评论内容中人工判断该 PR 是否应被阻塞。

这会造成几个问题：

- 对外部贡献者的 code PR，重要问题没有转化为 GitHub 原生的 `REQUEST_CHANGES`，branch protection 无法把 Bot 的阻塞判断纳入 merge gate。
- 对 Bot 评审意见的含义缺少统一规则：`verdict`、GitHub review event、human reviewer request 和最终 merge gate 之间容易混淆。
- 对 non-member PR 的人工复核需求缺少自动化路径。Bot approve 一个外部 code PR 时，应该能请求一个合格 CODEOWNERS reviewer，而不是只留下机器评论。

## 3. Goals

- 扩展 `review-pr` 和 `review-spec` 的 `review.json` 契约，要求输出 `verdict`，取值为 `APPROVE` 或 `REJECT`。
- 支持可选 `recommended_reviewers`，仅在 workflow 需要请求人工 reviewer 的场景中使用。
- 按 PR 作者身份、PR 类型和 `verdict` 映射 GitHub review event。
- 仅在 `non-member code PR + verdict = REJECT` 时发布 GitHub `REQUEST_CHANGES`。
- 在 `non-member code PR + verdict = APPROVE` 时尝试请求 1 个 human reviewer。
- 从 `.github/CODEOWNERS` 中选择、校验或 fallback human reviewer。
- 对成员、协作者、owner、bot/automation user、spec-only PR 保持低风险行为：发布 `COMMENT`，不自动请求 human reviewer。
- 在 `author_association` 缺失或异常时采用保守行为：不把作者当作 non-member，发布 `COMMENT`。
- 明确 `verdict` 不是最终 merge 决策；最终能否 merge 仍由 GitHub branch protection、required checks、code owner review 和权限共同决定。

## 4. Non-goals

- 不改变 GitHub branch protection 规则。
- 不保证 Bot 的 `APPROVE` 会让 PR 可合并。
- 不为 spec-only PR 启用 non-member reviewer request flow。
- 不支持一次请求多个 human reviewers。
- 不从 GitHub live API 动态推断 reviewer 列表；reviewer 来源限定为仓库中的 `.github/CODEOWNERS`。
- 不允许 agent 任意指定 CODEOWNERS 之外的 reviewer。
- 不把 bot/automation user 当作 non-member 处理。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub Actions、review skill 和发布脚本的行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### `review.json` 输出体验

- `review-pr` / `review-spec` 必须输出合法 JSON。
- `review.json` 必须包含：
  - `verdict`: `"APPROVE"` 或 `"REJECT"`。
  - `body`: 顶层评审总结或无法 inline 的问题。
  - `comments`: inline review comments 数组。
- `review.json` 可以包含：
  - `recommended_reviewers`: 字符串数组，仅在需要请求 human reviewer 时使用。
- 当没有阻塞级问题时，`verdict` 为 `APPROVE`。
- 当存在会导致实现、规格、测试、权限、安全、数据流或用户行为明显错误的重要问题时，`verdict` 为 `REJECT`。
- `💡 [SUGGESTION]` 和 `🧹 [NIT]` 不应单独导致 `REJECT`。
- 对 spec-only PR，`review-spec` 仍可输出 `REJECT` 表示文档质量不满足要求，但发布到 GitHub 时仍使用 `COMMENT`。

### PR 作者身份判断

- `ORG_MEMBER_ASSOCIATIONS = {"COLLABORATOR", "MEMBER", "OWNER"}`。
- 如果 PR author 的 `author_association` 在上述集合中，视为 member / collaborator / owner。
- 如果 PR author 的 `author_association` 不在上述集合中，且作者不是 bot/automation user，视为 non-member。
- 如果作者是 bot/automation user，不视为 non-member。
- 如果 `author_association` 缺失、为空或无法识别，系统必须采用保守行为：不视为 non-member，按普通 `COMMENT` 发布。

### PR 类型判断

- code PR：changed files 不全在 `specs/` 下。
- spec-only PR：changed files 非空，且全部路径以 `specs/` 开头。
- spec-only PR 不作为 non-member code review subject 处理；无论作者身份和 `verdict` 如何，都只发布 `COMMENT`，不请求 human reviewer。

### GitHub review event 映射

| PR 作者 | PR 类型 | `verdict` | GitHub review event | 是否请求 human reviewer |
| --- | --- | --- | --- | --- |
| member / collaborator / owner | code PR | `APPROVE` | `COMMENT` | 否 |
| member / collaborator / owner | code PR | `REJECT` | `COMMENT` | 否 |
| non-member | code PR | `APPROVE` | `COMMENT` | 是，尝试请求 1 个 reviewer |
| non-member | code PR | `REJECT` | `REQUEST_CHANGES` | 否 |
| non-member | spec-only PR | `APPROVE` / `REJECT` | `COMMENT` | 否 |

### Human reviewer 选择

- Human reviewer 来源是 `.github/CODEOWNERS`。
- 当 `non-member code PR + verdict = APPROVE` 时，workflow 尝试请求 1 个 reviewer。
- Agent 可以在 `review.json.recommended_reviewers` 中返回一个 reviewer。
- `recommended_reviewers` 必须满足：
  - 是字符串数组。
  - 最多只包含 1 个 reviewer。
  - reviewer 不能是 PR 作者本人。
  - reviewer 必须出现在 `.github/CODEOWNERS`。
- 如果 agent 没有返回 reviewer，或返回的 reviewer 结构合法但不合格，workflow 自行 fallback：
  - 按 PR changed files 顺序查找。
  - 对每个 path 使用 `.github/CODEOWNERS` 最后一个匹配规则。
  - 取该规则中第一个合格 owner。
  - 如果 changed path 没有匹配规则，取 CODEOWNERS 文件中第一个合格 owner。
- 如果没有可用 CODEOWNERS owner，workflow 不请求 reviewer，但仍成功发布 review comment，不应因为无法请求 reviewer 阻断整个 Bot review。

### GitHub merge gate 语义

- `verdict` 是 Bot 的机器判断。
- GitHub review event 是 Bot 对机器判断的发布形式。
- Branch protection 才是最终 merge gate。
- `REQUEST_CHANGES` 可能阻塞 merge，但是否阻塞取决于仓库保护规则和维护者权限。
- `COMMENT` 不应被描述为批准或拒绝 GitHub merge。
- 对 spec-only PR，`review-spec` 的 `verdict` 只用于机器可读地表达文档评审结论，并保证 review body 中的结论与结构化结果一致；发布到 GitHub 时不会成为 blocking review。

## 7. Success criteria

- `review-pr` 和 `review-spec` 的输出说明要求 `review.json` 包含 `verdict`。
- `validate_review_json.py` 接受并校验 `verdict`，且拒绝非 `APPROVE` / `REJECT` 值。
- `validate_review_json.py` 接受并校验可选 `recommended_reviewers`。
- `post_pr_review.py` 不再固定发布 `COMMENT`，而是按本规格表格选择 `COMMENT` 或 `REQUEST_CHANGES`。
- 对 member / collaborator / owner PR，无论 code PR 的 `verdict` 是 `APPROVE` 还是 `REJECT`，GitHub event 都是 `COMMENT`。
- 对 non-member code PR，当 `verdict = REJECT` 时，GitHub event 是 `REQUEST_CHANGES`。
- 对 non-member code PR，当 `verdict = APPROVE` 时，GitHub event 是 `COMMENT`，并尝试请求 1 个 CODEOWNERS reviewer。
- 对 non-member spec-only PR，无论 `verdict` 如何，都只发布 `COMMENT` 且不请求 reviewer。
- Bot/automation author、缺失或异常 `author_association` 都不会走 non-member blocking flow。
- 当 agent 给出的 `recommended_reviewers` 结构合法但 reviewer 不合格时，workflow 使用 CODEOWNERS fallback，而不是失败。结构不合法的 `recommended_reviewers` 仍由 validator 拒绝。
- 当没有可用 CODEOWNERS reviewer 时，workflow 不请求 reviewer，但发布 review 本身仍可完成。

## 8. Validation

- 增加或更新单元测试覆盖 `post_pr_review.py` 的 event 映射矩阵。
- 增加或更新单元测试覆盖 bot author、缺失 `author_association`、spec-only PR 的保守分支。
- 增加或更新单元测试覆盖 `recommended_reviewers` 校验和 CODEOWNERS fallback。
- 增加或更新单元测试覆盖 `validate_review_json.py` 对 `verdict` 和 `recommended_reviewers` 的 schema 校验。
- 人工检查 `review-pr` / `review-spec` skill 文档，确认它们描述的新 `review.json` 契约与 validator 一致。
- 使用一个 sample `review.json` 验证 `APPROVE`、`REJECT`、无 inline comments、有 inline comments 的输出都能通过 validator。

## 9. Open questions

- `review-pr` / `review-spec` 判定 `REJECT` 的边界是否应严格绑定到 `🚨 [CRITICAL]` 和 `⚠️ [IMPORTANT]`，还是允许顶层 `body` 中的阻塞问题触发 `REJECT`？本规格建议按“是否存在阻塞级问题”判断，而不是只按 inline severity 机械判断。
- 如果 CODEOWNERS owner 是 team slug，GitHub reviewer request 是否应支持 `team_reviewers`？当前规格只要求请求 1 个 reviewer，优先按用户 reviewer 实现。
