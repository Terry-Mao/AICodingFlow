---
type: concept
title: 项目安装脚本
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-07
review_due: 2026-09-05
sources:
  - docs/product/raw/project-installer.md
---

# 项目安装脚本

项目安装脚本 `install.sh` 用于把 AICodingFlow 管理的 workflow automation 和 Codex skills 同步到目标项目。

## 当前规则

- 安装入口可以是本地 clone 后运行 `./install.sh --target /path/to/target-repo`，也可以是远程一行命令。
- 远程一行安装会先 clone AICodingFlow 源仓库，避免误把当前工作目录当作安装源。
- `--target` 未提供时使用当前目录；目标必须是已存在目录。
- `--dry-run` 只报告将同步或跳过的内容，不写入目标项目。

## 同步边界

- 同步范围包括 `.agents/skills/`、`.agents/contracts/`、`.github/skills/`、`.github/agents/`、`.github/scripts/` 和 `.github/workflows/`。
- `.github/skills/*-repo/SKILL.md` 不由安装脚本安装；目标项目已有 repo-local companion skills 会保留。
- 目标项目 `.github` 下不属于同步目录的文件不会被删除。
- `.github/aicodingflow-tests/` 是上游托管测试目录，默认不会安装到目标项目；目标项目自己的 `.github` 相关测试应优先放在 `.github/tests/`。
- AICodingFlow 源仓库中的 `.github/workflows/ci.yml` 是参考最小 CI，不会同步到目标项目；目标项目应保留自己的 CI 编排，并在 CI 成功路径中 dispatch 已安装的 `review-pr.yml`。
- 安装脚本不初始化 issue triage 配置；首次接入时可后续手动运行 `$bootstrap-issue-config`。

## Supporting Summaries

- [项目安装脚本摘要](../summaries/project-installer.md)

## Related Concepts

- [Issue triage 初始化配置](issue-triage-bootstrap.md)
- [Repo-specific duplicate guidance](repo-specific-duplicate-guidance.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
- [Agent 目录布局](agent-directory-layout.md)
- [Product Wiki Query agent](product-wiki-query-agent.md)
