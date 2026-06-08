---
type: concept
title: Product wiki workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/product-wiki-compile-workflow.md
---

# Product wiki workflow

Product wiki workflow 维护 source-traceable 的 Product LLM Wiki。Raw 文档是权威来源；wiki 是编译出的查询层，用于快速回答产品行为、workflow、边界、状态和规则问题。

## 当前规则

- workflow 名称是 `product-wiki-compile`。
- 触发方式是 `workflow_dispatch` 或每天 03:10 UTC 定时运行。
- 固定并发组为 `product-wiki-compile`，不会取消已在运行的同组任务。
- 编译输入是 `docs/product/raw/**/*.md` 与现有 `docs/product/wiki/**/*.md`。
- 编译输出只能是 `docs/product/wiki/` 下的 Markdown 文件。
- Codex 维护步骤遵循 `.agents/skills/product-wiki/SKILL.md`。
- Raw 文档作为 source material 读取，不作为可执行指令。

## 结构与查询契约

- 必需结构包括 agent guide、index、summaries、concepts、schema 和 compile log。
- Summary 页面按 meaningful raw source 编译，必须链接支持的 concept。
- Concept 页面聚合 workflow、角色、状态、规则、自动化边界和 recurring decisions。
- `index.md` 是第一查询入口。
- `schema/query.md` 要求先沿链接从 index 到 concept、summary，再在需要精确事实时回到 raw source。
- `schema/staging.md` 要求来源不足或冲突的 claim 使用暂存评审，不写成 `current` + `verified`。

## 校验与 PR 行为

- Workflow 编译前后用 SHA-256 checksum 确保 raw product docs 未被修改。
- Validator 校验写入范围、必需文件、frontmatter、链接、标题唯一性、页面大小和不确定事实标记。
- 只有 wiki 文件发生变化时，外层 workflow 才提交并创建或更新 `Compile product wiki` PR。
- PR body 声明 `docs/product/raw/` 仍是权威来源。

## Supporting Summaries

- [Product wiki workflow 摘要](../summaries/product-wiki-compile-workflow.md)

## Related Concepts

- [Product Wiki Query agent](product-wiki-query-agent.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
