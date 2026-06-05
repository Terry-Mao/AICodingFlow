---
type: summary
title: Create issue skill 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/create-issue-skill.md
---

# Create issue skill 摘要

Source: [docs/product/raw/create-issue-skill.md](../../raw/create-issue-skill.md)

`create-issue` skill 把用户请求、显式 issue 文本或当前对话上下文转换成 GitHub issue。它是本地开发流入口，目标是先创建可分诊、可审查的问题，再进入分支、提交、推送和 PR 流程。

## 模板与正文

- Skill 读取 `.github/ISSUE_TEMPLATE.md` 以及 `.github/ISSUE_TEMPLATE/` 下的 Markdown 和 YAML issue forms。
- `.github/ISSUE_TEMPLATE/config.yml` 或 `config.yaml` 只用于判断 blank issue 是否禁用、是否存在外部联系方式；contact links 不视为模板。
- 模板选择基于请求和模板 metadata；多个模板同样匹配且会改变必填字段或 metadata 时，需要先确认。
- Issue 标题和正文只能使用用户请求、附件或当前对话支持的事实，不得虚构版本、日志、labels、assignees、milestones、日期、优先级或环境信息。

## 创建边界

- 默认不添加分类 labels；自动 triage 仓库由后续 workflow 负责分类、复现度和重复检测。
- 只有用户显式要求，或模板需要明确非分类 routing label 时，才传递 label。
- 用户明确要求创建 issue 且 repository、模板或 plain fallback、标题、正文和 metadata 都明确时，skill 可以直接创建；draft、prepare 或 write issue 需要先确认。
- 创建使用 `gh issue create` 和临时 body file；`gh` 不可用、未认证或无权限时，不使用 `gh api` 或 raw HTTP fallback。

## 安全报告

- 涉及漏洞、exploit、secret、credential、私有客户数据等敏感安全问题时，默认不得创建公开 issue。
- Skill 应先查找 private vulnerability reporting、`SECURITY.md` 或仓库声明的私密披露渠道。
- 只有用户明确确认适合公开披露且已完全脱敏时，才可创建公开 issue；body 不得包含原始 secrets、tokens、credentials、private keys、exploit payloads、个人联系方式或私有客户数据。

## 支持的概念

- [Create issue skill](../concepts/create-issue-skill.md)
