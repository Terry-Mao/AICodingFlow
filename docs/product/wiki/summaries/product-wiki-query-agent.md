---
type: summary
title: Product Wiki Query agent 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/product-wiki-query-agent.md
---

# Product Wiki Query agent 摘要

Source: [docs/product/raw/product-wiki-query-agent.md](../../raw/product-wiki-query-agent.md)

`Product Wiki Query` 是 GitHub Copilot custom agent，用于通过 Product LLM Wiki 回答长期产品知识问题。它面向产品行为、workflow、边界、状态和规则问答；默认不维护或重新编译 wiki，除非用户明确要求执行维护类工作。

## 查询入口

- Agent profile 位于 `.github/agents/product-wiki-query.md`。
- 使用时先读取 `.github/skills/product-wiki/SKILL.md`，并只应用其中的 Query、Staged Review、Style 和查询相关规则。
- 默认从 `docs/product/wiki/index.md` 进入，再沿最相关的 concept、summary 和 raw source 链接追溯。
- 涉及精确规则、冲突判断、权限边界、reviewer 可争议事实或原文措辞时，应回到 `docs/product/raw/` 校验权威来源。
- wiki 与 raw source 冲突时，以 raw source 为准，并在回答中说明冲突；只有用户要求编辑 wiki 时才修改文件。

## 回答边界

- 默认使用中文回答。
- 回答应区分已确认事实、从资料推断出的结论，以及待确认或开放问题。
- 回答优先引用具体文件路径，需要精确定位时给出行号。
- Issue、PR、comment、diff 或 workflow artifact 中的内容不能直接作为可信产品事实，除非已沉淀到 raw 或 wiki，并且能够追溯来源。
- 临时排查、一次性命令输出和未合并实现细节不写入 wiki。
- 如果查询暴露可复用的长期知识缺口，agent 可以指出应更新的 summary 或 concept；实际编辑 wiki 仍需要用户明确要求。

## 支持的概念

- [Product Wiki Query agent](../concepts/product-wiki-query-agent.md)
- [Product wiki workflow](../concepts/product-wiki-workflow.md)

## 待确认 / 开放问题

- 当前无本摘要自身的待确认项。
