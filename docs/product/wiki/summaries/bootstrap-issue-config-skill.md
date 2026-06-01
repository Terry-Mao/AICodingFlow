---
type: summary
title: Issue triage 初始化配置 skill 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/bootstrap-issue-config-skill.md
---

# Issue triage 初始化配置 skill 摘要

Source: [docs/product/raw/bootstrap-issue-config-skill.md](../../raw/bootstrap-issue-config-skill.md)

`bootstrap-issue-config` skill 用于把仓库初始化为可被 issue triage agent 稳定识别标签、路径和负责人。它面向首次接入 issue 自动 triage 的仓库。

## 产出

- 生成或更新 `.github/issue-triage/config.json`，记录 triage agent 可使用的 GitHub label 定义。
- 生成或更新 `.github/CODEOWNERS`，按路径记录熟悉相关区域的 GitHub 用户，用于 triage、review 和 owner 推断。
- `config.json` 顶层只包含 `labels` key；labels 以精确 label name 为 key。
- 基础 labels 包括 `bug`、`enhancement`、`documentation`、`needs-info`、`duplicate`、`triaged`、`repro:*`，以及已有或推断出的 area、feature、status labels。

## 初始化行为

- skill 会读取现有 labels、最近 issues、issue templates、已有 triage config、已有 CODEOWNERS 和最近贡献记录。
- 仓库 labels 很少或不存在时，会 seed 基础 feature/status/repro labels。
- 初始化是 additive 和幂等的：重复运行不会删除旧 label 配置，也不会重复写入已有 CODEOWNERS 行。
- 已有 GitHub label 会跳过，缺失 label 才需要创建。
- bootstrap 不创建空的 repository companion skills；这些文件应由后续有证据支持的 self-improvement 流程或维护者编辑按需出现。

## 支持的概念

- [Issue triage 初始化配置](../concepts/issue-triage-bootstrap.md)
- [Issue triage workflow](../concepts/issue-triage-workflow.md)

