---
type: concept
title: CI failure diagnosis
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/ci-failure-diagnosis-skill.md
---

# CI failure diagnosis

CI failure diagnosis 是只读诊断流程：它从 GitHub Actions 状态和失败日志推断 root cause，并输出修复计划。

## 当前规则

- 目标可以来自 Actions run URL、run ID、branch name、当前 checkout 关联 PR 或当前分支最近失败 run。
- 找不到失败目标时停止，不生成无证据诊断。
- CI 仍在运行时，应区分已失败、已通过和仍运行的 checks，并建议等待最终结果。
- 诊断必须基于失败步骤日志、必要的 job 日志或 artifacts。
- 语言、包管理器、测试框架或构建工具只能在日志或仓库文件明确显示时写成事实。

## 输出边界

- 输出是修复计划，不是代码修改。
- skill 不直接修改代码、提交、推送或创建 PR。
- 没有日志证据时不假设失败原因。

## Supporting Summaries

- [CI failure diagnosis skill 摘要](../summaries/ci-failure-diagnosis-skill.md)

## Related Concepts

- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)

