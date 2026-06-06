---
type: summary
title: Agent 目录布局摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-06
review_due: 2026-09-04
sources:
  - docs/product/raw/agent-directory-layout.md
---

# Agent 目录布局摘要

Source: [docs/product/raw/agent-directory-layout.md](../../raw/agent-directory-layout.md)

AICodingFlow 使用根目录 `AGENTS.md` 作为共享仓库级 agent guidance，并使用 `.agents/` 保存共享 workflow skills。Claude、Codex 和 Cursor 通过各自期望的入口读取同一组仓库规则、skills 和工具规则，避免在多个工具目录中维护重复配置。

## 共享入口

- `AGENTS.md` 是 Codex 默认加载的仓库级 agent guidance 权威入口。
- `CLAUDE.md -> AGENTS.md` 让 Claude Code 加载同一份仓库级 guidance。
- `.agents/skills/` 存放可复用 workflow skills。
- `.claude/skills` 指向 `../.agents/skills`。
- `.codex/skills` 指向 `../.agents/skills`。
- `.cursor/rules/agents.mdc` 是 Cursor 专用规则文件。
- 产品目标是让 Claude、Codex 和 Cursor 使用同一组仓库规则与 workflow skills。

## Windows symlink 支持

- 仓库把 `CLAUDE.md` 以及 `.claude`、`.codex` 和 `.cursor` 中的共享技能入口记录在 Git 中。
- `CLAUDE.md` 与 Claude/Codex skills 入口使用 symlink 指向共享内容。
- Windows 环境应优先启用 Git 真实 symlink checkout，例如 clone 前设置 `core.symlinks=true`，并确保系统允许创建 symlink。
- 如果 Windows clone 时禁用 symlink，`CLAUDE.md`、`.claude/skills` 或 `.codex/skills` 可能被检出为普通文本文件；修复方式是重新启用 symlink 支持，移除占位文件，并从 Git 恢复对应路径。
- 目录 junction 只适合作为无法使用真实 symlink 的本地 fallback，不是 tracked symlink 路径的默认设置方式。

## 支持的概念

- [Agent 目录布局](../concepts/agent-directory-layout.md)
- [项目安装脚本](../concepts/project-installer.md)
