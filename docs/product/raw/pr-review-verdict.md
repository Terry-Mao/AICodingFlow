# PR review verdict 与 non-member gate

自动 PR review 会把 `review-pr` / `review-spec` 产出的机器评审结论写入
`review.json.verdict`，并由发布流程把该结论映射为 GitHub review event。
`verdict` 是 Bot 的机器判断，不直接等同于 GitHub 的最终 merge gate。

## 触发与 reviewable 条件

AI PR Review 默认由目标项目的 CI 成功路径通过 `workflow_dispatch` 输入 PR number
触发。AICodingFlow 仓库自带的参考 `CI` workflow 会在非 draft、同仓库 head PR 上运行
单元测试和 Python 编译检查，成功后 dispatch `review-pr.yml`；目标项目已有自己的 CI
时，应在自己的 CI 成功路径中 dispatch `review-pr.yml`，而不是修改已安装的
`review-pr.yml`。

AI PR Review 也可以手动通过 `workflow_dispatch` 输入 PR number 触发。当 open 且非
draft 的 PR conversation comment 中包含发给 Actions variable `AGENT_LOGIN` 指定账号的
body-level command `@AGENT_LOGIN /review` 时，也可以从 `issue_comment` 事件触发。
手动触发和 comment 触发会先解析目标 PR，再复用 review 流程。`review-pr.yml` 不直接监听
GitHub `pull_request` 事件。

`workflow_dispatch` 触发的 review workflow 允许 `github-actions[bot]` 运行 Codex
review action，因此使用 GitHub Actions 自带 `GITHUB_TOKEN` 的 CI dispatch 可以运行 AI
PR Review。若目标仓库改用 GitHub App token、PAT 或第三方 CI dispatch，actor 可能不是
`github-actions[bot]`，需要让 `review-pr.yml` 的 bot allowlist 与实际触发 actor 匹配，
或改用有人类账号权限的 token 触发。

Comment 触发要求命令独占一行，允许前后空白；裸 `/review`、单纯 `@AGENT_LOGIN`
mention、quoted line、fenced code block、普通句子中的提及，以及带额外参数的
`@AGENT_LOGIN /review ...` 都不会触发 AI review。普通 issue comment 和 PR inline
review comment 也不是该入口。

只有 open、非 draft 且 head repository 与当前仓库一致的 PR 会继续进入 AI review。
closed PR、draft PR 或来自 fork 的 PR 会被跳过，不会运行 agent、发布 review 或上传
review artifact。

## Comment 与手动触发的 PR 关联

当 AI PR Review 由 PR comment 或 `workflow_dispatch` 触发，且目标 PR 的 head
repository 是当前仓库时，workflow 会在 PR head commit 上写入 `AI PR Review` commit
status。Review 运行开始时 status 为 `pending`，运行结束后按 job 结果更新为
`success` 或 `failure`，并把 status target URL 指向对应的 GitHub Actions run。

该 commit status 用于让 CI dispatch、comment 或手动触发的 review run 出现在目标 PR 的
checks / statuses 视图中。AICodingFlow 参考 `CI` workflow 在测试前会先把
`AI PR Review` status 写为 `pending`；测试失败或被跳过时写为 `failure`，表示 CI 未通过所以
不会运行 AI review；dispatch 失败时也写为 `failure`。review workflow 运行后再按 review
job 结果更新该 status。来自 fork 的 PR 不会写入该 status。

## Review skill 选择

AI PR Review 会先按 changed files 判断 PR 类型，再选择仓库本地 review companion
skill：

- spec-only PR 使用 `review-spec-repo`。
- 其他 code PR 使用 `review-pr-repo`。

`review-pr-repo` 和 `review-spec-repo` 是 AICodingFlow 仓库对核心
`review-pr` / `review-spec` 工作流的仓库本地包装器，用于补充本仓库的评审偏好，
不改变核心输出契约。

Code PR review 会在基础 `review-pr` 评审之外应用 `security-review-pr` 补充安全检查；
spec-only PR review 会在基础 `review-spec` 评审之外应用 `security-review-spec`
补充设计层安全检查。安全发现不会生成单独输出，而是合并进同一个 `review.json`。

`security-review-pr` 关注代码层面的安全问题，包括输入校验、注入风险、鉴权与权限检查、
secrets 管理、弱加密或错误随机数、依赖与 supply chain、敏感数据处理，以及不安全默认配置。
`security-review-spec` 关注 spec 设计层安全缺口，包括 threat surface、trust boundary、
鉴权与授权模型、敏感数据与 secrets 处理、滥用或 DoS 风险、依赖边界、配置默认值，以及
安全相关可观测性。

安全补充只报告有证据的问题，不运行动态扫描，不查询外部安全 API，不制造理论风险，也不直接发布
GitHub comment。安全发现的 review comment 使用 `[SECURITY]` 标签，并计入同一个
`review.json.verdict` 判断；critical security finding 通常应导致 `REJECT`。

## 本地 review 入口

本地开发完成但尚未 push 或创建 PR 时，可以使用 `review-pr-local` 或
`review-spec-local` 在当前分支运行与 GitHub review workflow 一致的评审流程。
两个本地 skill 会先准备根目录快照，再分别委托给 `review-pr-repo` 或
`review-spec-repo`。

本地 review 输入与输出固定在仓库根目录：

- `pr_description.txt`
- `pr_diff.txt`
- `spec_context.md`，仅 code review 需要且存在可用 spec context 时生成
- `.local_review_baseline.status`
- `review.json`

准备 `pr_description.txt` 时，本地 review 优先读取当前分支关联的 GitHub PR metadata。
如果无法获取关联 PR，则回退到基于本地仓库状态构造的 PR metadata。`pr_diff.txt` 不使用
GitHub PR diff，始终基于当前 worktree 相对选定 base 的完整状态生成；当当前分支可解析到
GitHub PR 且用户未显式传入 base 时，选定 base 使用该 PR metadata 中的真实 base SHA。

本地 review 准备阶段支持 worktree 中已有 staged、unstaged 和未跟踪文件改动。准备脚本会
删除旧的 review 快照，并基于当前 worktree 相对选定 base 的完整状态生成 `pr_diff.txt`；
未被 Git ignore 的未跟踪文件会纳入 diff，根目录 review 快照文件和
`.local_review_baseline.status` 不会纳入 diff。

`.local_review_baseline.status` 记录准备阶段完成后的业务文件 dirty 状态，并被 Git ignore。
review 阶段只能写入受控 review 输出文件，不得修改源码、workflow、测试、spec 或 skill
文件；校验会允许 baseline 中已存在的业务文件状态继续存在，但会拒绝新增业务文件改动、
业务文件状态变化、staged 输出、非 review 快照文件变更，以及 review 输出被意外删除。

本地 review 的 base 可以显式传入；显式 base 拥有最高优先级，并会同步反映在
`pr_description.txt` 的 base metadata 中。未显式传入 base 时，已有 GitHub PR 的当前分支优先
使用该 PR 的 base SHA；没有可用 PR base SHA 时，本地 fallback 按 `origin/main`、
`upstream/main`、`main` 的优先级解析。当 worktree 没有未提交修改时，本地 diff 仍表示当前
head 相对 base 的提交差异；当同时存在已提交和未提交修改时，本地 diff 覆盖两者合并后的当前
文件状态。code review 会根据本地 diff 中的 changed files 解析 spec context；spec-only
review 不生成 spec context。

## Review 输出契约

`review.json` 必须包含：

- `verdict`: `APPROVE` 或 `REJECT`。
- `body`: 顶层评审总结或无法 inline 的问题。
- `comments`: inline review comments 数组。

`review.json` 可以包含 `recommended_reviewers`，该字段只用于需要推荐人工
reviewer 的场景。`recommended_reviewers` 必须是字符串数组，最多包含 1 个
reviewer。

`APPROVE` 表示没有阻塞级发现。`REJECT` 表示存在需要修复后再合并的阻塞级发现。
建议和 nit 不应单独导致 `REJECT`。

## PR 作者与类型

作者身份按 GitHub PR 的 `author_association` 判断：

- `COLLABORATOR`、`MEMBER`、`OWNER` 视为 member / collaborator / owner。
- 其他非空、可识别身份在作者不是 bot 或 automation user 时视为 non-member。
- bot / automation user 不视为 non-member。
- `author_association` 缺失、为空或异常时采用保守行为，不视为 non-member。

PR 类型按 changed files 判断：

- code PR：changed files 不全在 `specs/` 下。
- spec-only PR：changed files 非空，且全部路径以 `specs/` 开头。

spec-only PR 不进入 non-member blocking 或 reviewer request flow。

## GitHub review event 映射

| PR 作者 | PR 类型 | `verdict` | GitHub review event | 人工 reviewer |
| --- | --- | --- | --- | --- |
| member / collaborator / owner | code PR | `APPROVE` | `COMMENT` | 不请求 |
| member / collaborator / owner | code PR | `REJECT` | `COMMENT` | 不请求 |
| non-member | code PR | `APPROVE` | `COMMENT` | 尝试请求 1 个 reviewer |
| non-member | code PR | `REJECT` | `REQUEST_CHANGES` | 不请求 |
| non-member | spec-only PR | `APPROVE` 或 `REJECT` | `COMMENT` | 不请求 |

只有 `non-member code PR + verdict = REJECT` 会发布 GitHub `REQUEST_CHANGES`。
其他场景默认发布 `COMMENT`，避免 Bot 对成员 PR 或 spec-only PR 产生过强的
merge gate 影响。

## Human reviewer 选择

当 `non-member code PR + verdict = APPROVE` 时，workflow 尝试请求 1 个 human
reviewer。Reviewer 来源限定为仓库中的 `.github/CODEOWNERS`。

如果 agent 返回 `recommended_reviewers`，workflow 会校验 reviewer：

- 必须是字符串。
- 最多只能有 1 个。
- 不能是 PR 作者本人。
- 必须出现在 `.github/CODEOWNERS`。

如果没有可用推荐，或推荐 reviewer 不合格，workflow 使用 CODEOWNERS fallback：
按 changed files 顺序查找最后匹配的 CODEOWNERS 规则，并取该规则中第一个合格
owner；如果 changed path 没有匹配规则，则取 CODEOWNERS 文件中第一个合格
owner。

如果没有可用 CODEOWNERS owner，workflow 不请求 reviewer，但 Bot review 发布仍可
完成。

## Merge gate 语义

`verdict` 只表达 Bot 的机器判断。GitHub review event 是 Bot 对该判断的发布形式。
最终能否 merge 仍由 GitHub branch protection、required checks、code owner review、
blocking `REQUEST_CHANGES` 和维护者权限共同决定。

来源：PR #55，PR #65，PR #67，PR #79，PR #81，PR #82，PR #89，PR #90，PR #93，PR #103，
PR #116，PR #154，PR #155，Issue #115，Issue #152，`specs/issue-51/product.md`，
`specs/issue-77/product.md`，`specs/issue-85/product.md`，`specs/issue-115/product.md`。
