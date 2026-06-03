---
type: concept
title: Agent 目录布局
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-03
review_due: 2026-09-01
sources:
  - docs/product/raw/agent-directory-layout.md
---

# Agent 目录布局

Agent 目录布局定义 AICodingFlow 如何用 `.agents/` 作为共享配置源，并向不同 AI coding 工具提供它们期望的本地入口。

## 当前规则

- `.agents/AGENTS.md` 是仓库级 agent guidance 的权威入口。
- `.agents/skills/` 是可复用 workflow skills 的共享目录。
- Claude 入口通过 `.claude/CLAUDE.md` 和 `.claude/skills` 指向 `.agents/` 中的共享内容。
- Codex 入口通过 `.codex/AGENTS.md` 和 `.codex/skills` 指向 `.agents/` 中的共享内容。
- Cursor 使用 `.cursor/rules/agents.mdc` 作为专用规则文件。
- 该布局让 Claude、Codex 和 Cursor 读取同一组仓库规则与 workflow skills，而不是维护独立副本。

## Windows symlink 规则

- `.claude`、`.codex` 和 `.cursor` 作为普通目录被记录在 Git 中。
- Claude 和 Codex 的共享入口依赖 tracked symlink。
- Windows clone 应优先启用真实 symlink checkout；禁用 symlink 时，Git 可能把共享入口检出为普通文本占位文件。
- 禁用 symlink 导致占位文件时，应重新启用 symlink 支持，移除占位文件，并从 Git 恢复 `.claude` 和 `.codex`。
- 目录 junction 只适合作为无法使用真实 symlink 的本地 fallback，不是默认设置方式。

## Supporting Summaries

- [Agent 目录布局摘要](../summaries/agent-directory-layout.md)

## Related Concepts

- [项目安装脚本](project-installer.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
