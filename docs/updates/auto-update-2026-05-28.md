# 产品变更报告：2026-05-28

扫描窗口：`2026-05-28T00:00:00Z`（含）至 `2026-05-29T00:00:00Z`（不含）。

## 用户可见变更

- 新增 product-docs-sync 自动化：合并后的实现 PR 可进入长期产品文档同步判断，agent 产出 `required`、`uncertain` 或 `not-needed` 决策；需要更新或确认时，外层 workflow 会创建或更新 `docs/product/` 文档同步 PR。来源：PR #179。
- `create-pr` 指引现在只复用当前分支上的 open PR；同名分支曾经存在的 merged 或 closed PR 不再阻止创建新的 PR，避免实现完成后误更新旧 PR 或无法开新 PR。来源：PR #191。相关 issue：https://github.com/Terry-Mao/AICodingFlow/issues/178。

## Bug fixes

- Product change report 生成与校验路径现在禁止在报告中暴露 commit ID，并要求 related issue 引用使用 linked issue metadata 中的 GitHub issue URL；报告状态校验会拦截疑似 SHA token 和缺失 issue URL 的相关 issue 引用，同时避免把 `PR #...` 误判为 related issue。来源：PR #181。
- Product docs sync 扫描合并 PR 时会跳过自身生成的文档同步 PR，避免自动文档同步 PR 再次触发同一同步流程。来源：PR #187。
- Product docs sync 的 issue 提取现在同时识别 PR 标题和描述中的 `Refs #...`、`References #...`、`Fixes #...` 等引用，并继续优先保留 GitHub `closingIssuesReferences`；普通 PR 或 pull request 编号文本不会被误当作 issue。来源：PR #188。

## 行为变更

- Product docs sync 从单个 merged PR 触发扩展为 scheduled/manual 扫描模式：未指定 PR 时会按 UTC 扫描窗口查找合并 PR，按 `mergedAt` 与 PR 编号排序，选择 ledger 中尚未处理的第一个 PR，并把 `not-needed` 决策也写入 `docs/product/.product-docs-sync-ledger.json`，减少重复扫描。来源：PR #184。
- Product docs sync 改为使用固定累计分支 `docs/product-docs-sync`，后续运行会更新同一个 open 文档同步 PR；PR body 会从 ledger 汇总每个已处理源 PR 的决策、影响文档和变更摘要。来源：PR #187。
- 长期产品文档补齐了 product change report 的来源引用规则：报告不得包含 commit ID，related issue 引用必须使用 GitHub issue URL。来源：PR #182，源 PR #181。
- 长期产品文档补齐了自动实现 workflow 的 spec context 优先级、默认目标分支、agent 职责和外层 workflow 职责，并记录了 PR review verdict、non-member gate、spec workflow gating 与 implementation workflow 触发语义。来源：PR #185、PR #189。
- Product change report automation 生成了 `2026-05-27` 的时间序列报告，并在 ledger 中记录该扫描窗口覆盖的 PR，减少后续重复报告。来源：PR #183。

## 内部工程变更

- Product docs sync 新增上下文准备、结果校验、PR body 生成和 ledger 更新脚本，并补充 workflow 与脚本契约测试，覆盖扫描窗口、写入边界、决策 schema、累计 PR body 和自身 PR 过滤。来源：PR #179、PR #184、PR #187。
- Product docs sync 的长期文档同步结果已在 ledger 中记录：PR #50 为 `not-needed`，PR #52、PR #55、PR #56 和 PR #58 为 `required`，PR #53 为 `not-needed`。来源：PR #185、PR #186、PR #189。
- Product change report 的 markdown context 不再输出 merge commit 或 commits 计数，workflow prompt 与状态校验统一执行“无 commit ID、issue URL 可追踪”的报告契约。来源：PR #181。
- `create-pr` skill guidance 增加回归测试，确保 open PR 查找使用 `gh pr list --state open --head` 的 URL 结果，并禁止回退到可能解析 closed/merged PR 的 `gh pr view` 存在性检查。来源：PR #191。

## 风险或待验证

- Product docs sync 现在依赖 `docs/product/.product-docs-sync-ledger.json` 选择下一个未处理 PR；如果累计 PR rebase 或 ledger 写入失败，后续 scheduled run 可能重复处理同一源 PR，需关注 workflow 运行结果。来源：PR #184、PR #187。
- Product docs sync 的 referenced issue 解析基于 PR 标题和描述中的关键词匹配；异常格式的 issue 引用可能不会进入 specs 读取流程，后续如出现漏读，应扩展解析规则并补充测试。来源：PR #188。
- Product change report 的 commit ID 拦截会扫描报告正文中的 SHA-like token；如果未来报告需要记录非 commit 的长十六进制标识，可能需要调整校验规则或改用更明确的表达。来源：PR #181。

## 可能需要同步的长期文档

- Product docs sync 的 scheduled/manual 扫描、固定累计 PR、ledger 处理和自身 PR 过滤已经改变长期 workflow 行为；如果 `docs/product/raw/` 尚未覆盖这些规则，应同步更新长期产品文档。来源：PR #184、PR #187、PR #188。
- `create-pr` 的 open-PR-only 复用规则属于 agent 工作流长期契约；如果长期产品文档或 contributor 文档描述了 PR 创建策略，应补充 closed/merged 同名分支 PR 不可复用的行为。来源：PR #191。相关 issue：https://github.com/Terry-Mao/AICodingFlow/issues/178。

## Source references

- PR #179: https://github.com/Terry-Mao/AICodingFlow/pull/179
- PR #181: https://github.com/Terry-Mao/AICodingFlow/pull/181
- PR #182: https://github.com/Terry-Mao/AICodingFlow/pull/182
- PR #183: https://github.com/Terry-Mao/AICodingFlow/pull/183
- PR #184: https://github.com/Terry-Mao/AICodingFlow/pull/184
- PR #185: https://github.com/Terry-Mao/AICodingFlow/pull/185
- PR #186: https://github.com/Terry-Mao/AICodingFlow/pull/186
- PR #187: https://github.com/Terry-Mao/AICodingFlow/pull/187
- PR #188: https://github.com/Terry-Mao/AICodingFlow/pull/188
- PR #189: https://github.com/Terry-Mao/AICodingFlow/pull/189
- PR #191: https://github.com/Terry-Mao/AICodingFlow/pull/191
- Related issue reference: https://github.com/Terry-Mao/AICodingFlow/issues/178
