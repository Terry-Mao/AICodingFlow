# 产品变更报告：2026-05-29

扫描窗口：`2026-05-29T00:00:00Z`（含）至 `2026-05-30T00:00:00Z`（不含）。

## 用户可见变更

- 新增产品 LLM Wiki 自动编译能力：`docs/product/raw/` 可定期或手动编译为 `docs/product/wiki/` 下的索引、摘要、概念页、schema 和编译日志，便于 agent 与维护者按可追踪知识层查询产品行为。来源：PR #193、PR #195。
- Product Wiki 契约从 compile-only 扩展为 `product-wiki` 技能，补充 Query 流程、staged review schema、wiki health 元数据与更严格的链接/日期校验；后续 wiki 页面需要保持 source traceability、查询入口和待确认内容的结构化表达。来源：PR #201。
- 新增 GitHub Copilot custom agent `product-wiki-query`，安装模板时会同步 `.github/agents`，使下游仓库可以按 Product Wiki Query 流程回答产品知识问题。来源：PR #204。
- Product Docs Sync scheduled run 从每日 UTC 02:45 调整为每小时第 45 分钟运行，保持手动触发、权限、concurrency、ledger 和 docs 写入边界不变。来源：PR #194。相关 issue：https://github.com/Terry-Mao/AICodingFlow/issues/192。

## Bug fixes

- 长期产品文档补正 AI PR Review 手动触发契约：PR conversation comment 需要使用 body-level `@AGENT_LOGIN /review` 命令；裸 mention、行内命令、draft 或非 open PR 等无效形式会被跳过。来源：PR #203，源 PR #82。
- 长期产品文档补充 comment-triggered 与 manual AI PR Review run 的 PR 关联和 commit status 语义：同仓库 PR 会在 head commit 上发布 AI PR Review 状态，并关联到对应运行结果。来源：PR #205，源 PR #89。

## 行为变更

- 长期产品文档补齐了自动 implementation workflow、spec workflow 和 PR review verdict 的一批既有契约，包括 implementation 分支选择、handoff 文件边界、workflow trigger gate、review companion skill、本地 review 入口以及 spec PR 不再自动 review 等行为。来源：PR #190。
- Product Docs Sync 将 spec plan approval 的长期生命周期行为写入 authoritative raw docs：`plan-approved` 会移除 linked issue 上的 `ready-to-spec`，并且只有 issue 已具备 `ready-to-implement` 和目标 agent assignment 时才可能继续派发 implementation。来源：PR #198，源 PR #66。
- Product Wiki 编译结果在初次生成后继续随 raw docs 与 wiki contract 变化增量更新，包括新增 AI PR Review workflow、本地 review 入口、issue readiness、agent workflow 边界等概念页和摘要页；`docs/product/raw/` 仍是 authoritative source。来源：PR #195、PR #196、PR #200。
- Product change report automation 生成了 `2026-05-28` 的时间序列报告，并在 ledger 中记录该扫描窗口覆盖的 PR，减少后续重复报告。来源：PR #197。

## 内部工程变更

- Product Wiki 自动化新增 workflow、skill、PR body helper、写入边界校验和回归测试，校验 required files、summary/concept frontmatter、wiki internal links、Markdown-only write surface 与 raw docs 不可变约束。来源：PR #193。
- Product Wiki 校验进一步收紧 metadata、health checks、query/staging schema、invalid review date 和链接完整性，并将 workflow prompt 切换到扩展后的 `product-wiki` 契约。来源：PR #201。
- Product Docs Sync 的长期文档同步结果继续累积到固定文档同步 PR：本次记录了 PR #66、PR #82 和 PR #89 等源 PR 的 required docs updates，并更新 implementation、spec 与 PR review verdict raw docs。来源：PR #198、PR #203、PR #205。
- 安装脚本测试覆盖 `.github/agents` 同步，README 仓库目录说明加入 GitHub Copilot custom agents 交付路径。来源：PR #204。

## 风险或待验证

- Product Wiki 编译结果是 raw docs 的派生知识层；如果编译页与 `docs/product/raw/` 冲突，应以 raw docs 为准，并在后续 wiki 编译中修正或标记待确认。来源：PR #193、PR #195、PR #201。
- Product Wiki validation 现在依赖更严格的 metadata、链接和 review date 规则；后续手工编辑 wiki 页面时，需要保持 index、summary、concept 和 schema 的链接闭环，否则 scheduled compile PR 可能被校验拦截。来源：PR #201。
- Product Docs Sync 改为每小时运行后，对 ledger、固定累计分支和 open PR 更新路径的稳定性要求更高；如果累计 PR 长时间未合并，后续同步内容会持续堆叠在同一个 PR 中。来源：PR #194、PR #198、PR #203、PR #205。

## 可能需要同步的长期文档

- Product Wiki 的 Query/staging schema、`product-wiki-query` custom agent 和安装交付路径改变了模板可用能力；如果长期产品文档或安装文档尚未覆盖这些用户入口，应补充说明。来源：PR #201、PR #204。
- AI PR Review 的 `@AGENT_LOGIN /review` 命令、comment/manual run commit status、以及 spec plan approval 后的 issue state synchronization 已通过 Product Docs Sync 更新 raw docs；如 wiki 或其他衍生文档仍引用旧的裸 mention 或自动 review 语义，应由后续 wiki 编译同步。来源：PR #198、PR #203、PR #205。

## Source references

- PR #190: https://github.com/Terry-Mao/AICodingFlow/pull/190
- PR #193: https://github.com/Terry-Mao/AICodingFlow/pull/193
- PR #194: https://github.com/Terry-Mao/AICodingFlow/pull/194
- PR #195: https://github.com/Terry-Mao/AICodingFlow/pull/195
- PR #196: https://github.com/Terry-Mao/AICodingFlow/pull/196
- PR #197: https://github.com/Terry-Mao/AICodingFlow/pull/197
- PR #198: https://github.com/Terry-Mao/AICodingFlow/pull/198
- PR #200: https://github.com/Terry-Mao/AICodingFlow/pull/200
- PR #201: https://github.com/Terry-Mao/AICodingFlow/pull/201
- PR #203: https://github.com/Terry-Mao/AICodingFlow/pull/203
- PR #204: https://github.com/Terry-Mao/AICodingFlow/pull/204
- PR #205: https://github.com/Terry-Mao/AICodingFlow/pull/205
- Related issue reference: https://github.com/Terry-Mao/AICodingFlow/issues/192
