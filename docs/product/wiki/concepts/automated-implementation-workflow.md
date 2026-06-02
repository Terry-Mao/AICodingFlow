---
type: concept
title: 自动 implementation workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-02
review_due: 2026-08-31
sources:
  - docs/product/raw/implementation-workflow.md
---

# 自动 implementation workflow

自动 implementation workflow 负责把已经准备实现的 GitHub issue 派发给 Codex agent，并由外层 GitHub Actions 创建或更新 implementation PR。

## 产品行为

- 普通新 issue 不会直接进入实现阶段。
- workflow 支持手动触发，也支持 issue label、issue assignment 或 issue comment mention 触发。
- 自动事件只处理非 PR issue。
- issue 必须满足 `ready-to-implement` 与目标 agent assignment。
- Spec PR 的 `plan-approved` label 只表示该 PR 可作为实现上下文，不会单独触发 implementation workflow。
- PR comment 不触发 implementation workflow；PR comment mention 由 AI PR Review workflow 处理。
- 创建或更新 implementation PR 后不会自动触发 AI PR Review，因为 implementation PR 默认保持 draft。
- 需要 review 时，在 open 且非 draft PR 的普通 conversation comment 中发送 `@AGENT_LOGIN /review`。

## Workflow 文件写入

- 普通不修改 GitHub workflow 文件的实现分支使用默认 `GITHUB_TOKEN` 推送。
- 实现变更包含 `.github/workflows/` 下的 GitHub workflow 文件时，外层 workflow 会通过 `actions/create-github-app-token` 生成短期 GitHub App installation token，并作为 `WORKFLOW_UPDATE_TOKEN` 传给提交脚本。
- 仓库需要配置 `APP_CLIENT_ID` Actions variable 和 `APP_PRIVATE_KEY` Actions secret。
- 对应 GitHub App 必须安装到目标仓库，并具有 `Contents: Read and write` 与 `Workflows: Read and write` 权限。
- 生成出来的一次性 installation token 不应存成 secret。

## Supporting Summaries

- [自动实现 workflow 摘要](../summaries/implementation-workflow.md)

## Related Concepts

- [Issue ready label 与 agent assignment](issue-readiness-and-assignment.md)
- [Agent login 配置](agent-login-configuration.md)
- [Spec context 与目标分支选择](spec-context-and-target-branch.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
