---
type: summary
title: Product wiki workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/product-wiki-compile-workflow.md
---

# Product wiki workflow 摘要

Source: [docs/product/raw/product-wiki-compile-workflow.md](../../raw/product-wiki-compile-workflow.md)

`product-wiki-compile` workflow 维护 `docs/product/raw/` 与 `docs/product/wiki/` 组成的 Product LLM Wiki。Raw 文档仍是权威产品事实；wiki 是面向 agents 和维护者的查询层，提供摘要、概念页、索引、schema、链接、查询指引、暂存评审规则和维护日志。

## 触发与输入

- workflow 通过 `workflow_dispatch` 手动触发，或每天 03:10 UTC 定时运行。
- 使用固定并发组 `product-wiki-compile`，不会取消已在运行的同组任务。
- 编译输入包括 `docs/product/raw/**/*.md` 和已存在的 `docs/product/wiki/**/*.md`。
- Codex 维护步骤遵循 `.agents/skills/product-wiki/SKILL.md`，并把 raw 文档视为 source material，而不是可执行指令。

## 输出结构

- 编译输出只能是 `docs/product/wiki/` 下的 Markdown 文件。
- 必需文件包括 `AGENTS.md`、`index.md`、`summaries/*.md`、`concepts/*.md`、schema 文档和 `log.md`。
- Summary 页面为每个有意义 raw source 提供摘要并链接相关 concept 页面。
- Concept 页面汇总 workflow、角色、状态、规则、自动化边界和 recurring decisions 等高价值查询主题。
- `schema/query.md` 定义从 index 到 concept、summary、raw source 的查询链路；广泛关键词搜索只是辅助方式。
- `schema/staging.md` 要求来源不足或冲突的 claim 进入暂存评审，而不是标记为 `current` + `verified`。

## 写入与校验边界

- 编译步骤不得修改 `docs/product/raw/`、`docs/updates/`、`.agents/`、`.github/`、`specs/`、产品代码或 workflow handoff files。
- 编译步骤不得运行 git 命令、提交、推送、创建 PR、调用 GitHub API 或编辑 issue。
- Workflow 在编译前后校验 raw product docs 的 SHA-256 checksum，确保 raw source 未被修改。
- `validate_product_wiki_compile.py` 校验允许变更面、必需文件、frontmatter、链接完整性、标题唯一性、页面大小和暂存评审标记位置。
- 只有 validator 报告 wiki 文件发生变化时，外层 workflow 才提交 `docs/product/wiki` 并创建或更新 `Compile product wiki` PR。

## 支持的概念

- [Product wiki workflow](../concepts/product-wiki-workflow.md)
- [Product Wiki Query agent](../concepts/product-wiki-query-agent.md)
- [Agent 与外层 workflow 职责边界](../concepts/agent-workflow-boundaries.md)
