# PR review verdict 与 non-member gate

自动 PR review 会把 `review-pr` / `review-spec` 产出的机器评审结论写入
`review.json.verdict`，并由发布流程把该结论映射为 GitHub review event。
`verdict` 是 Bot 的机器判断，不直接等同于 GitHub 的最终 merge gate。

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

来源：PR #55，`specs/issue-51/product.md`。
