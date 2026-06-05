---
type: concept
title: Create issue skill
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/create-issue-skill.md
---

# Create issue skill

`create-issue` skill 将用户请求、显式 issue 文本或当前对话上下文转换成 GitHub issue。它的产品边界是创建可分诊、可审查的问题，不负责后续 triage、分支、提交、推送或 PR。

## 模板选择

- 读取根目录 `.github/ISSUE_TEMPLATE.md` 和 `.github/ISSUE_TEMPLATE/` 下的 Markdown/YAML issue forms。
- `.github/ISSUE_TEMPLATE/config.yml` 或 `config.yaml` 只用于 blank issue 与 contact links 判断。
- 根据模板文件名、名称、描述、默认标题、labels 和表单字段选择模板。
- 多个模板同样匹配且会改变必填字段或 metadata 时，需要先向用户确认。
- 无适配模板且 blank issue 未禁用时，可创建简洁 plain issue。

## 内容约束

- 标题和正文只能使用用户请求、附件或对话支持的事实。
- Markdown 模板保留有用标题和必填字段，移除提示性占位说明；未知必填字段写 `Not provided`。
- YAML issue forms 转换为 markdown body 后用 GitHub CLI 创建。
- 不得虚构版本、日志、labels、assignees、milestones、日期、优先级或环境信息。

## 创建边界

- 默认不添加分类 labels；自动 triage 仓库由后续 issue triage workflow 处理分类、复现度和重复检测。
- 只有用户显式要求，或模板需要非分类 routing label 时，才传递 label。
- Assignees、milestones 和 projects 只在用户显式要求或模板明确要求时设置。
- 创建时使用 `gh issue create` 和临时 body file；`gh` 不可用、未认证或无权限时，只报告可手动创建的内容，不使用 API fallback。

## 安全披露

- 涉及漏洞、exploit、secret、credential、私有客户数据等敏感安全问题时，默认不得创建公开 issue。
- 应优先查找 private vulnerability reporting、`SECURITY.md` 或仓库声明的私密披露渠道。
- 只有用户明确确认内容适合公开披露且已完全脱敏时，才可创建公开 issue。

## Related Concepts

- [Issue triage workflow](issue-triage-workflow.md)

## Supporting Summaries

- [Create issue skill 摘要](../summaries/create-issue-skill.md)
