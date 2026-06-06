# Product wiki compile workflow

`product-wiki-compile` workflow 用于把 `docs/product/raw/` 中的权威产品文档编译为
`docs/product/wiki/` 下的 LLM Wiki。Raw 文档仍是产品事实的权威来源；wiki 是面向 agents
和维护者的查询层，负责提供摘要、概念页、索引、schema、链接和编译日志。

## 触发方式

该 workflow 只通过两类入口运行：

- `workflow_dispatch` 手动触发。
- 定时任务，每天 03:10 UTC 运行一次。

Workflow 使用固定并发组 `product-wiki-compile`，不会取消已在运行的同组任务。

## 编译输入与输出

编译输入包括：

- `docs/product/raw/**/*.md`
- 已存在的 `docs/product/wiki/**/*.md`

编译输出只能是 `docs/product/wiki/` 下的 Markdown 文件。必需 wiki 文件包括：

- `docs/product/wiki/AGENTS.md`
- `docs/product/wiki/index.md`
- `docs/product/wiki/summaries/*.md`
- `docs/product/wiki/concepts/*.md`
- `docs/product/wiki/schema/README.md`
- `docs/product/wiki/schema/page-types.md`
- `docs/product/wiki/schema/linking.md`
- `docs/product/wiki/log.md`

Summary 页面应为每个有意义的 raw source 提供摘要并链接相关 concept 页面。Concept 页面用于汇总
workflow、角色、状态、规则、自动化边界和 recurring decisions 等高价值查询主题。Index 是
wiki 查询入口；log 记录本次编译新增或更新的页面、未解决冲突和待确认事实。

## 写入边界

Codex 编译步骤必须遵循 `.agents/skills/product-wiki-compile/SKILL.md`，并把
`docs/product/raw/` 视为 source material，而不是可执行指令。

编译步骤不得修改 `docs/product/raw/`、`docs/updates/`、`.agents/`、`.github/`、`specs/`、
产品代码或 workflow handoff files，也不得运行 git 命令、提交、推送、创建 PR、调用 GitHub API
或编辑 issue。外层 GitHub Actions workflow 负责所有 GitHub 写操作。

Workflow 在 Codex 编译前记录 raw product docs 的 SHA-256 checksum，并在编译后校验 checksum，
确保编译过程没有修改 raw source。

## 校验规则

`validate_product_wiki_compile.py` 负责校验 product wiki 编译结果：

- 允许的变更面仅限 `docs/product/wiki/` 下的 Markdown 文件；`product-wiki-raw.sha256`
  作为 workflow handoff 文件不视为 wiki 变更。
- 如果存在 raw sources 或 wiki 发生变更，必需 wiki 文件必须存在。
- Summary 和 concept 页面必须带有 frontmatter，包含 `type`、非空 `title` 和非空 `sources`。
- `docs/product/wiki/index.md` 必须链接到 `AGENTS.md`、schema 页面、`log.md`、所有 summary
  页面和所有 concept 页面。
- Summary 页面必须链接相关 concept 页面；concept 页面必须链接支持它的 summary 页面。
- 不确定或冲突信息应标记为 `待确认` 或 `开放问题`。

## PR 行为

Workflow 使用固定分支 `docs/product-wiki-compile` 承载编译结果。运行时先基于默认分支初始化或
rebase 该分支；只有 validator 报告 wiki 文件发生变化时，才提交 `docs/product/wiki` 并创建或更新
open PR。

创建或更新 PR 时，标题固定为 `Compile product wiki`，正文由
`write_product_wiki_compile_pr_body.py` 生成。PR body 会说明 source root、target root、触发来源、
变更文件和校验命令，并声明 `docs/product/raw/` 仍是权威来源。

来源：PR #193。
