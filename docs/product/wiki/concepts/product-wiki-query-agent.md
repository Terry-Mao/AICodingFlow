---
type: concept
title: Product Wiki Query agent
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/product-wiki-query-agent.md
  - docs/product/raw/agent-directory-layout.md
  - docs/product/raw/product-wiki-compile-workflow.md
---

# Product Wiki Query agent

`Product Wiki Query` 是面向 Product LLM Wiki 的 GitHub Copilot custom agent。它用于回答长期产品知识问题，不是默认的 wiki 维护或重新编译入口。

## 当前规则

- Agent profile 位于 `.github/agents/product-wiki-query.md`。
- 查询前读取 `.agents/skills/product-wiki/SKILL.md`，并只应用 Query、Staged Review、Style 和查询相关规则。
- 默认从 `docs/product/wiki/index.md` 开始，再沿 concept、summary 和 raw source 链接追溯。
- 面向产品行为、workflow、边界、状态和规则问答。
- 除非用户明确要求维护类工作，否则不维护或重新编译 wiki。
- 只有用户要求编辑 wiki 时才修改文件。

## 回答规则

- 默认使用中文回答。
- 区分已确认事实、从资料推断出的结论，以及待确认或开放问题。
- 涉及精确规则、冲突判断、权限边界、reviewer 可争议事实或原文措辞时，回到 `docs/product/raw/` 校验。
- wiki 与 raw source 冲突时，以 raw source 为准，并说明冲突。
- Issue、PR、comment、diff 或 workflow artifact 不能直接作为可信产品事实，除非已沉淀到 raw 或 wiki 并能追溯来源。
- 临时排查、一次性命令输出和未合并实现细节不写入 wiki。

## Supporting Summaries

- [Product Wiki Query agent 摘要](../summaries/product-wiki-query-agent.md)
- [Agent 目录布局摘要](../summaries/agent-directory-layout.md)
- [Product wiki workflow 摘要](../summaries/product-wiki-compile-workflow.md)

## Related Concepts

- [Product wiki workflow](product-wiki-workflow.md)
- [Agent 目录布局](agent-directory-layout.md)

## 待确认 / 开放问题

- 当前无本概念自身的待确认项。
