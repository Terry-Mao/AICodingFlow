# Compile Log

## 2026-06-11

按 `docs/product/raw/` 作为权威来源同步 agent 目录布局：

- 更新 [Agent 目录布局摘要](summaries/agent-directory-layout.md) 与 [Agent 目录布局](concepts/agent-directory-layout.md)：记录 `.agents/skills/` 只承载本地开发与共享 skills，`.github/skills/` 承载 GitHub Actions workflow-only skills，并由 workflow prompt 显式读取。
- 更新 [项目安装脚本摘要](summaries/project-installer.md) 与 [项目安装脚本](concepts/project-installer.md)：记录安装同步 `.github/skills/`，但不安装 repo-specific `*-repo` companion skills。
- 更新 review、product wiki、dedupe 和 update workflow 相关 summary/concept，统一 workflow-only skill 路径为 `.github/skills/`。
- 复核 Product LLM Wiki，并修正 issue triage lifecycle label 的来源状态。

- 更新 [Issue triage workflow 摘要](summaries/issue-triage-workflow.md) 与 [Issue triage 结果契约](concepts/issue-triage-result-contract.md)：不再把 `ready-to-spec` / `ready-to-implement` 的 triage 输出边界写成已确认受保护规则，改为 `needs-review` + `source_status: conflict` 并放入专门 `待确认` 章节。
- 复核 22 个 raw source 均有对应 source summary，现有 Ingest、Query、Linter、schema 和 index 结构保持齐全。

## 待确认 / 开放问题

- 待确认：`ready-to-implement` 和 `ready-to-spec` 的最终 triage 输出边界需要产品确认；core skill reserved-label 规则与 repo companion lifecycle label guidance 仍需统一。
- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- `docs/product/raw/issue-triage-workflow.md` 记录 `ready-to-implement` / `ready-to-spec` 的输出边界存在 core skill 规则与 repo companion guidance 之间的待确认差异。

## 2026-06-10

按 `docs/product/raw/` 作为权威来源同步 Product LLM Wiki 的产品文档同步行为：

- 更新 [产品文档同步 workflow 摘要](summaries/product-docs-sync-workflow.md) 与 [产品文档同步 workflow](concepts/product-docs-sync-workflow.md)：记录产品文档同步 PR body/comment 的长度保护、历史 ledger 摘要和超长字段截断规则。
- 新增 [update-triage workflow 摘要](summaries/update-triage-workflow.md) 与 [update-triage 自进化 triage 规则 workflow](concepts/update-triage-workflow.md)：补齐 `docs/product/raw/update-triage-workflow.md` 的 source traceability、维护者反馈学习规则、写入边界和 PR 行为。
- 更新 [index.md](index.md)：链接新增 update-triage summary 与 concept，使 22 个 raw source 均有对应 summary。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-09

按 `docs/product/raw/` 作为权威来源复核 Product LLM Wiki，并校准近期 raw source 中已经确认的新规则：

- 更新 [产品文档同步 workflow 摘要](summaries/product-docs-sync-workflow.md) 与 [产品文档同步 workflow](concepts/product-docs-sync-workflow.md)：触发方式改为定时任务与 `workflow_dispatch`，补充 UTC 扫描窗口、自同步 PR 跳过、linked issue 解析、ledger、固定同步分支、`not-needed` PR 行为和追加 PR comment 规则。
- 更新 [PR review verdict 与 non-member gate 摘要](summaries/pr-review-verdict.md)、[AI PR Review workflow](concepts/ai-pr-review-workflow.md)、[Comment / manual review status](concepts/comment-manual-review-status.md) 与 [本地 PR review 入口](concepts/local-pr-review-entrypoints.md)：记录 `review-pr.yml` 不直接监听 `pull_request`、默认由 CI 成功后 dispatch、本地 review 根目录快照和受控输出文件。
- 重新校验 21 个 raw source 均有对应 summary，index 链接全部 summary、concept、schema、Agent guide 与 compile log。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-08

按 `docs/product/raw/` 作为权威来源复核 Product LLM Wiki，保持现有 Ingest、Query 与 Linter 结构：

- 确认 21 个 raw source 均已有对应 source summary，且 summary 与 concept 保持双向查询链路。
- 确认 [index.md](index.md) 链接 Agent guide、schema、compile log、全部 summary 和全部 concept。
- 确认 [schema/query.md](schema/query.md) 保留 index -> concept -> summary -> raw source 的查询顺序，宽泛关键词搜索仍仅作为辅助。
- 确认 [schema/staging.md](schema/staging.md) 保留不确定事实的 staged review gate，避免将来源不足或冲突内容写成 `current` + `verified`。
- 未发现新增 raw source、缺失 summary、缺失 concept 链接或 raw source 之间的新冲突。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-07

根据 `docs/product/raw/` 重新核对 wiki，补齐新增 raw source 的 source traceability，并校准既有概念覆盖：

- 新增 [Create PR skill 摘要](summaries/create-pr-skill.md) 与 [Create PR skill](concepts/create-pr-skill.md)，记录当前 head branch open PR 复用、closed/merged PR 不复用、PR body 人工补充保留和 skill 职责边界。
- 新增 [Product wiki workflow 摘要](summaries/product-wiki-compile-workflow.md) 与 [Product wiki workflow](concepts/product-wiki-workflow.md)，记录编译触发、输入输出、query/staging schema、raw checksum、validator 和 PR 行为。
- 新增 [Product Wiki Query agent 摘要](summaries/product-wiki-query-agent.md) 与 [Product Wiki Query agent](concepts/product-wiki-query-agent.md)，记录 GitHub Copilot custom agent 的查询入口、raw 校验规则、回答边界和默认不维护 wiki 的边界。
- 更新 [index.md](index.md)，链接新增 summary 与 concept。
- 校准 [Agent 目录布局摘要](summaries/agent-directory-layout.md) 与 [Agent 目录布局](concepts/agent-directory-layout.md)：补充 `.github/agents/` 和 `Product Wiki Query` custom agent 的产品定位。
- 校准 [项目安装脚本摘要](summaries/project-installer.md) 与 [项目安装脚本](concepts/project-installer.md)：同步范围包含 `.github/agents/`。
- 扩展 [Agent 与外层 workflow 职责边界](concepts/agent-workflow-boundaries.md)：补齐 `create-pr`、`product-wiki-compile` 和 `Product Wiki Query` 的职责边界。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-06

根据 `docs/product/raw/` 重新核对 wiki，修正与 raw source 不一致或覆盖不足的页面：

- 校准 [Agent 目录布局摘要](summaries/agent-directory-layout.md) 与 [Agent 目录布局](concepts/agent-directory-layout.md)：仓库级 guidance 权威入口是根目录 `AGENTS.md`，`CLAUDE.md -> AGENTS.md`，Claude/Codex skills 入口指向 `.agents/skills/`。
- 补充 [项目安装脚本摘要](summaries/project-installer.md) 与 [项目安装脚本](concepts/project-installer.md)：AICodingFlow 源仓库的 `.github/workflows/ci.yml` 是参考最小 CI，不会同步到目标项目。
- 扩展 [产品变更报告摘要](summaries/product-change-reports.md) 与 [产品变更报告](concepts/product-change-reports.md)：记录 UTC 扫描、单日/区间路径、语言选择、ledger 状态、写入边界和 no-update 行为。
- 更新 [Agent 与外层 workflow 职责边界](concepts/agent-workflow-boundaries.md)，补齐 `update-pr-review`、`product-change-report` 和 `product-docs-sync` 的来源链路与边界。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-05

根据 `docs/product/raw/` 重新编译 wiki，补齐 raw source 到 summary/concept 的查询链路：

- 新增 [Agent 输出语言策略摘要](summaries/agent-language-policy.md) 与 [Agent 输出语言策略](concepts/agent-language-policy.md)，记录中文默认、人类可读字段范围、上下文语言选择和集中管理规则。
- 新增 [Create issue skill 摘要](summaries/create-issue-skill.md) 与 [Create issue skill](concepts/create-issue-skill.md)，记录模板选择、内容事实边界、metadata 传递、`gh issue create` 使用和安全报告处理。
- 新增 [产品文档同步 workflow 摘要](summaries/product-docs-sync-workflow.md) 与 [产品文档同步 workflow](concepts/product-docs-sync-workflow.md)，记录 merged PR 触发、稳定上下文、`product-docs-sync-result.json` 决策合同、写入范围和 draft review gate。
- 新增 [update-pr-review workflow 摘要](summaries/update-pr-review-workflow.md) 与 [update-pr-review 自进化 review 规则 workflow](concepts/update-pr-review-workflow.md)，记录人类反馈学习信号、companion guidance 路由、写入范围和 PR 行为。
- 更新 [index.md](index.md)，链接新增 summary 与 concept。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-03

根据 `docs/product/raw/` 重新编译 wiki，补齐新增或此前未覆盖的 raw source，并修正与 raw source 不一致的事实：

- 新增 [Agent 目录布局摘要](summaries/agent-directory-layout.md) 与 [Agent 目录布局](concepts/agent-directory-layout.md)，记录 `.agents/` 共享入口、Claude/Codex/Cursor 本地入口和 Windows symlink 规则。
- 更新 [index.md](index.md)，链接新增 summary 与 concept。
- 校准 [项目安装脚本摘要](summaries/project-installer.md) 与 [项目安装脚本](concepts/project-installer.md)：默认安装不再同步 `.github/aicodingflow-tests/`；该目录保留为 AICodingFlow 上游测试资产，目标项目自有 `.github` 测试应优先放在 `.github/tests/`。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-02

根据 `docs/product/raw/` 重新编译 wiki，补齐此前未覆盖的 raw source，并校准与 raw source 不一致的旧事实：

- 新增 [项目安装脚本摘要](summaries/project-installer.md) 与 [项目安装脚本](concepts/project-installer.md)，记录 `install.sh` 的入口、同步范围、repo-local companion 保留规则和 bootstrap 边界。
- 新增 [update-dedupe workflow 摘要](summaries/update-dedupe-workflow.md) 与 [update-dedupe 自进化规则 workflow](concepts/update-dedupe-workflow.md)，记录 duplicate evidence、repeated cluster、写入范围和 PR 行为。
- 更新 [index.md](index.md)，链接所有新增 summary 与 concept。
- 校准 issue triage 的 needs-info follow-up 触发规则。
- 校准 implementation 和 PR comment response workflow 文件写入权限说明：workflow 文件变更由外层 workflow 通过 GitHub App installation token 设置 `WORKFLOW_UPDATE_TOKEN`，仓库需配置 `APP_CLIENT_ID` 与 `APP_PRIVATE_KEY`。
- 校准 PR comment response 授权与上下文规则：私有仓库中具备写权限的 `CONTRIBUTOR` 可被授权；agent 使用稳定本地快照，不额外 fetch GitHub context。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-06-01

根据 `docs/product/raw/` 重新编译 wiki，并补齐所有当前 raw source 的查询链路：

- 新增 6 个 source summary：
  - [Issue triage workflow 摘要](summaries/issue-triage-workflow.md)
  - [Issue triage 初始化配置 skill 摘要](summaries/bootstrap-issue-config-skill.md)
  - [Repo-specific dedupe guidance companion 摘要](summaries/dedupe-guidance-companion.md)
  - [PR comment response workflow 摘要](summaries/pr-comment-response-workflow.md)
  - [Merge conflict resolution skill 摘要](summaries/merge-conflict-resolution-skill.md)
  - [CI failure diagnosis skill 摘要](summaries/ci-failure-diagnosis-skill.md)
- 新增 issue triage、dedupe companion、PR comment response、CI diagnosis 和 merge conflict resolution 相关 concept 页面。
- 更新 [index.md](index.md)，确保链接所有 summary、concept、schema、agent guide 和 compile log。
- 校准 [本地 Git helper skills 摘要](summaries/local-git-helper-skills.md) 与 [本地 Git helper skills](concepts/local-git-helper-skills.md)：worktree 路径保留分支目录层级，base 选择优先 `origin/<base>`，fetch 仅在影响结果时检查。
- 校准 [本地 PR review 入口](concepts/local-pr-review-entrypoints.md) 与 [PR review verdict 与 non-member gate 摘要](summaries/pr-review-verdict.md)：本地 review base 优先显式 base，其次 PR base SHA，再按 `origin/main`、`upstream/main`、`main` fallback。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-05-31

根据 `docs/product/raw/` 重新编译 wiki，并补齐 PR review raw source 中未单独建模的查询链路：

- 更新 [PR review verdict 与 non-member gate 摘要](summaries/pr-review-verdict.md)，补充 comment / manual 触发时的 `AI PR Review` commit status，以及安全补充 review 的输出边界。
- 新增 [Comment / manual review status](concepts/comment-manual-review-status.md)，追踪 PR comment 与 `workflow_dispatch` review run 如何写入同仓库 PR head commit status。
- 新增 [安全补充 review](concepts/security-review-supplements.md)，追踪 `security-review-pr` / `security-review-spec` 的适用范围、输出合并规则和证据边界。
- 更新 [AI PR Review workflow](concepts/ai-pr-review-workflow.md)、[PR review verdict](concepts/pr-review-verdict.md) 与 [index.md](index.md) 的相关链接。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-05-30

根据 `docs/product/raw/` 重新编译 wiki，并补齐新增 raw source 的查询链路：

- 新增 [本地 Git helper skills 摘要](summaries/local-git-helper-skills.md)，覆盖 `git-worktree` 的目录、分支、base、fetch、已有目标处理和安全边界。
- 新增 [本地 Git helper skills](concepts/local-git-helper-skills.md) concept，便于查询本地 Git 辅助能力的产品边界。
- 更新 [index.md](index.md)，链接新增 summary 与 concept。
- 校准 [PR review verdict 与 non-member gate 摘要](summaries/pr-review-verdict.md) 和 [本地 PR review 入口](concepts/local-pr-review-entrypoints.md)：本地 review 准备阶段支持已有 staged、unstaged 和未跟踪改动，并通过 `.local_review_baseline.status` 保护 review 阶段写入边界。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。

## 2026-05-29

重新编译 `docs/product/raw/` 的权威产品文档，并校验现有 LLM Wiki 结构：

- 保持查询入口：[index.md](index.md) 与 [AGENTS.md](AGENTS.md)。
- 扩展 schema 文档：[schema/README.md](schema/README.md)、[schema/page-types.md](schema/page-types.md)、[schema/linking.md](schema/linking.md)、[schema/query.md](schema/query.md)、[schema/staging.md](schema/staging.md)。
- 为 summary 与 concept frontmatter 增加 `status`、`confidence`、`source_status`、`owner`、`last_reviewed` 和 `review_due`。
- 增加 Query 沉淀规则与暂存评审规则，避免未确认内容被写成当前事实。
- 复核 `docs/product/raw/spec-workflow.md`，补充 spec approval 同步、implementation dispatch 条件、PR review 触发方式和 closed PR 不复用规则。
- 复核 `docs/product/raw/implementation-workflow.md`，补充 `pr-metadata.json` / `intended_files` 契约、workflow 文件 token 要求和 draft implementation PR 不自动 review 规则。
- 复核 `docs/product/raw/pr-review-verdict.md`，补充 comment command 精确匹配规则，并为缺失 frontmatter 的 PR review concept 页面补齐 linter 必需字段。
- 校验 4 个 raw source 对应的 summary：
  - [summaries/spec-workflow.md](summaries/spec-workflow.md)
  - [summaries/implementation-workflow.md](summaries/implementation-workflow.md)
  - [summaries/pr-review-verdict.md](summaries/pr-review-verdict.md)
  - [summaries/product-change-reports.md](summaries/product-change-reports.md)
- 新增 2 个 PR review concept 页面：
  - [concepts/ai-pr-review-workflow.md](concepts/ai-pr-review-workflow.md)
  - [concepts/local-pr-review-entrypoints.md](concepts/local-pr-review-entrypoints.md)
- 校验 11 个 concept 页面，覆盖 workflow 触发、agent login、spec context、职责边界、AI PR Review 触发、本地 review、PR review verdict、non-member gate 和产品变更报告。

## 待确认 / 开放问题

- 待确认：raw source 未详细描述 spec agent 的全部输出文件契约，只说明外层 workflow 创建或更新 spec PR。

## 冲突

- 未发现 raw source 之间的明确冲突。
