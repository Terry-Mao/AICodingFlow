# Agent 输出语言策略

AICodingFlow 的 agent-facing workflow 默认把人类可读输出写成中文。Agent 在生成 issue、
PR 标题与正文、commit message summary、spec、review comments、状态报告、产品更新报告
以及 workflow metadata 等内容时，应优先跟随最强相关上下文的主要自然语言。

## 语言选择规则

最强相关上下文包括用户最新请求、issue 标题和正文、PR 或 spec 文本，以及正在更新的既有文档。
如果已有文档使用明确语言，编辑时应保持该文档语言。上下文混合或不明确时，默认使用中文。

语言策略只适用于人类可读内容。代码标识符、路径、label、branch name、API name、issue
reference、命令、日志和引用输出保持原样，不因输出语言策略而翻译。

Workflow metadata 中的人类可读字段同样适用默认中文策略，例如 `pr_title`、`pr_summary`
和 `implementation_summary.md`。文件名、字段名和机器可读结构保持原样。

## 集中管理

根目录 `AGENTS.md` 是仓库级 agent guidance 的权威入口，负责声明默认语言偏好。
具体 skills 和 GitHub Actions prompt 不需要重复维护独立的语言选择规则；它们应继承仓库级
guidance，并继续保留各自任务的具体行为、文件边界和验证要求。

该集中策略避免不同 workflow 在 spec 创建、技术方案、产品更新报告等产物中使用互相冲突的
语言规则。

来源：PR #172，Issue #170；PR #175；PR #176。
