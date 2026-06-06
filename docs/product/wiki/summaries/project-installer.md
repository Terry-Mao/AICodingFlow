---
type: summary
title: 项目安装脚本摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-06
review_due: 2026-09-04
sources:
  - docs/product/raw/project-installer.md
---

# 项目安装脚本摘要

Source: [docs/product/raw/project-installer.md](../../raw/project-installer.md)

AICodingFlow 提供仓库级安装脚本 `install.sh`，用于把 workflow automation 和 Codex skills 同步到目标项目。它面向新项目接入和已有项目刷新，不负责初始化目标项目的 issue triage 配置，也不覆盖目标项目自己的 repo-local companion skills。

## 安装入口

- 从 AICodingFlow 仓库 clone 后运行 `./install.sh --target /path/to/target-repo`。
- 通过远程一行命令下载脚本并执行；远程执行会先 clone AICodingFlow 源仓库，再运行真实安装流程。
- `--target` 未提供时使用当前目录；目标路径必须已经是目录。
- 脚本依赖 `bash`、`git` 和 `rsync`；远程一行安装还需要 `curl`。

## 同步范围

- 安装同步 `.agents/skills/`、`.github/scripts/`、`.github/aicodingflow-tests/` 和 `.github/workflows/`。
- 普通 skills 可以复制或更新。
- `.agents/skills/*-repo/SKILL.md` 这类仓库本地 companion skills 不会安装到目标项目；目标项目已有 companion skills 会保留。
- 目标项目 `.github` 下不属于同步目录的文件不会被删除。
- `.github/aicodingflow-tests/` 是 AICodingFlow 上游托管的 workflow/script 测试目录，目标项目自己的 `.github` 相关测试应优先放在 `.github/tests/`。
- AICodingFlow 源仓库中的 `.github/workflows/ci.yml` 是参考最小 CI，不会同步到目标项目；目标项目应保留自己的 CI 编排，并在 CI 成功路径中 dispatch 已安装的 `review-pr.yml`。
- AICodingFlow 源仓库自己的 `test_install_script.py` 不会安装到目标项目。

## 预览与后续初始化

- `--dry-run` 只报告将同步或跳过的内容，不写入目标项目文件，也不创建目标目录结构。
- 首次接入 issue triage 自动化时，可在安装后手动运行 `$bootstrap-issue-config`。
- bootstrap 会使用 GitHub CLI 分析目标仓库 labels、issues 和 contributors，并可能创建 GitHub labels 或更新 `.github/CODEOWNERS`。
- bootstrap 不是安装脚本的一部分，也不需要定期运行。

## 支持的概念

- [项目安装脚本](../concepts/project-installer.md)
- [Issue triage 初始化配置](../concepts/issue-triage-bootstrap.md)
- [Agent 目录布局](../concepts/agent-directory-layout.md)
