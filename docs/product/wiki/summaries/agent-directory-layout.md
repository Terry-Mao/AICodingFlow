---
type: summary
title: Agent 目录布局摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-03
review_due: 2026-09-01
sources:
  - docs/product/raw/agent-directory-layout.md
---

# Agent 目录布局摘要

Source: [docs/product/raw/agent-directory-layout.md](../../raw/agent-directory-layout.md)

AICodingFlow 使用 `.agents/` 作为共享 agent 配置目录，并通过 Claude、Codex 和 Cursor 各自期望的本地入口暴露同一组仓库规则、skills 和工具规则，避免在多个工具目录中维护重复配置。

## 共享入口

- `.agents/AGENTS.md` 是仓库级 agent guidance 的权威入口。
- `.agents/skills/` 存放可复用 workflow skills。
- `.claude/CLAUDE.md` 指向 `../.agents/AGENTS.md`。
- `.claude/skills` 指向 `../.agents/skills`。
- `.codex/AGENTS.md` 指向 `../.agents/AGENTS.md`。
- `.codex/skills` 指向 `../.agents/skills`。
- `.cursor/rules/agents.mdc` 是 Cursor 专用规则文件。
- 产品目标是让 Claude、Codex 和 Cursor 使用同一组仓库规则与 workflow skills。

## Windows symlink 支持

- 仓库把 `.claude`、`.codex` 和 `.cursor` 作为普通目录记录在 Git 中。
- Claude 和 Codex 入口使用 symlink 指向 `.agents/` 中的共享文件。
- Windows 环境应优先启用 Git 真实 symlink checkout，例如 clone 前设置 `core.symlinks=true`，并确保系统允许创建 symlink。
- 如果 Windows clone 时禁用 symlink，相关路径可能被检出为普通文本文件；修复方式是重新启用 symlink 支持，移除占位文件，并从 Git 恢复 `.claude` 和 `.codex`。
- 目录 junction 只适合作为无法使用真实 symlink 的本地 fallback，不是 tracked symlink 路径的默认设置方式。

## 支持的概念

- [Agent 目录布局](../concepts/agent-directory-layout.md)
- [项目安装脚本](../concepts/project-installer.md)
