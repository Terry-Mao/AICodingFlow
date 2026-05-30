# CI failure diagnosis skill

`diagnose-ci-failures` skill 用于让 agent 基于 GitHub Actions 状态和失败日志诊断 CI
失败，并产出可审阅的修复计划。它是诊断入口，不负责直接修改代码、提交、推送或创建 PR。

## 适用入口

当用户要求检查 CI 状态、拉取 CI 问题、排查测试失败、调查 PR build failure，或提供
PR 分支、branch name、GitHub Actions run ID、Actions run URL 时，可以使用该 skill。

如果用户提供 Actions run URL 或 run ID，skill 直接查看对应 workflow run。如果用户提供
branch name，skill 会查找该分支最近失败的 workflow run。如果用户未提供明确目标，skill
先检查当前 checkout 是否关联 PR；有关联 PR 时优先读取该 PR 的失败 checks，没有关联 PR
时再回退到当前分支最近失败的 workflow run。

找不到失败的 PR check 或失败的 workflow run 时，skill 只报告未找到可诊断的失败目标并停止。

## 诊断范围

skill 会读取 CI 状态并区分已完成、运行中、成功和失败的 checks。CI 仍在运行时，结果应说明
哪些 checks 已失败或已通过，哪些 checks 仍在运行，并建议等待完成后再做最终诊断。

对失败的 run 或 check，skill 会提取失败步骤日志。必要时可以继续查看指定 job 的完整日志或
下载 run artifacts。诊断重点包括：

- 错误信息、文件路径和行号。
- build 或 compilation error。
- linting 或 formatting failure。
- test failure、失败测试名、stack trace 和 assertion 输出。
- environment failure，例如缺少 secret、权限问题、服务不可用、依赖安装失败或资源限制。

错误分类保持语言无关；只有日志或仓库文件明确显示具体语言、包管理器、测试框架或构建工具时，
才把它们作为观察事实写入诊断。

## 输出与边界

`diagnose-ci-failures` 的输出始终是修复计划。计划应包含问题概述、当前失败状态、基于日志的
root cause 分析、建议修改和验证步骤。

该 skill 只做诊断，不直接实现修复。它不得修改代码、提交、推送、创建 PR，或在没有日志证据时
假设失败原因。如果 CI 日志显示多个无关失败，计划应分组说明并建议按类别逐步修复。

来源：PR #112。
