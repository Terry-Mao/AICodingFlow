---
type: summary
title: CI failure diagnosis skill 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/ci-failure-diagnosis-skill.md
---

# CI failure diagnosis skill 摘要

Source: [docs/product/raw/ci-failure-diagnosis-skill.md](../../raw/ci-failure-diagnosis-skill.md)

`diagnose-ci-failures` skill 用于基于 GitHub Actions 状态和失败日志诊断 CI 失败，并产出可审阅的修复计划。它是诊断入口，不负责直接修改代码、提交、推送或创建 PR。

## 适用入口

- 用户要求检查 CI 状态、拉取 CI 问题、排查测试失败、调查 PR build failure 时使用。
- 用户提供 PR 分支、branch name、GitHub Actions run ID 或 Actions run URL 时可以定位目标。
- run URL 或 run ID 优先；branch name 会查找该分支最近失败的 workflow run。
- 未提供明确目标时，先检查当前 checkout 是否关联 PR；有关联 PR 时优先读取该 PR 的失败 checks，否则回退到当前分支最近失败的 run。
- 找不到失败目标时，只报告未找到可诊断失败并停止。

## 诊断范围

- 区分已完成、运行中、成功和失败的 checks。
- CI 仍在运行时，说明已失败、已通过和仍在运行的 checks，并建议等待完成后再做最终诊断。
- 对失败 run 或 check，提取失败步骤日志；必要时查看指定 job 完整日志或下载 artifacts。
- 诊断关注错误信息、文件路径与行号、build/compilation error、lint/formatting failure、test failure 和环境失败。
- 只有日志或仓库文件明确显示语言、包管理器、测试框架或构建工具时，才把它们作为观察事实。

## 输出边界

- 输出始终是修复计划，包含问题概述、当前失败状态、基于日志的 root cause 分析、建议修改和验证步骤。
- 不直接实现修复，不提交、推送、创建 PR，也不在缺少日志证据时假设失败原因。
- 多个无关失败应分组说明，并建议按类别逐步修复。

## 支持的概念

- [CI failure diagnosis](../concepts/ci-failure-diagnosis.md)

