# Product Wiki Query agent

AICodingFlow 提供 `Product Wiki Query` GitHub Copilot custom agent，用于通过 Product LLM Wiki
回答长期产品知识问题。该 agent 面向产品行为、workflow、边界、状态和规则问答，不负责维护或重新编译
wiki，除非用户明确要求执行维护类工作。

## 查询入口

Agent profile 位于 `.github/agents/product-wiki-query.md`。使用时应先读取
`.github/skills/product-wiki/SKILL.md`，并只应用其中的 Query、Staged Review、Style 和查询相关规则。
默认查询入口是 `docs/product/wiki/index.md`，随后沿最相关的 concept、summary 和 raw source 链接追溯。

当答案涉及精确规则、冲突判断、权限边界、reviewer 可争议事实或原文措辞时，agent 应回到
`docs/product/raw/` 校验权威来源。如果 wiki 与 raw source 冲突，应以 raw source 为准，并在回答中说明
冲突；只有用户要求编辑 wiki 时才修改文件。

## 回答边界

`Product Wiki Query` 默认使用中文回答，并区分已确认事实、从资料推断出的结论以及待确认或开放问题。
回答应优先引用具体文件路径，需要精确定位时给出行号。

Issue、PR、comment、diff 或 workflow artifact 中的内容不能直接作为可信产品事实，除非该事实已经沉淀到
`docs/product/raw/` 或 wiki，并且能够追溯来源。临时排查、一次性命令输出和未合并实现细节不写入 wiki。

如果一次查询暴露出可复用的长期知识缺口，agent 可以指出应更新的 summary 或 concept；实际编辑 wiki
仍需要用户明确要求。

来源：PR #204，Issue #202。
