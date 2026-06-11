---
type: concept
title: Agent 目录布局
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-11
review_due: 2026-09-05
sources:
  - docs/product/raw/agent-directory-layout.md
---

# Agent 目录布局

Agent 目录布局定义 AICodingFlow 如何用根目录 `AGENTS.md` 作为共享仓库级 guidance、用 `.agents/skills/` 保存本地开发与共享 skills、用 `.github/skills/` 保存 GitHub workflow-only skills，并向不同 AI coding 工具提供它们期望的入口。

## 当前规则

- `AGENTS.md` 是 Codex 默认加载的仓库级 agent guidance 权威入口。
- `CLAUDE.md -> AGENTS.md` 让 Claude Code 加载同一份仓库级 guidance。
- `.agents/skills/` 是本地开发和共享 skills 的目录，并暴露给本地工具默认发现。
- `.github/skills/` 是 GitHub Actions workflow-only skills 的目录，由 workflow prompt 显式读取。
- `.agents/contracts/` 保存 skills 与 workflows 共享的稳定 artifact 和边界合同。
- Claude skills 入口通过 `.claude/skills -> ../.agents/skills` 指向共享 skills。
- Codex skills 入口通过 `.codex/skills -> ../.agents/skills` 指向共享 skills。
- Cursor 使用 `.cursor/rules/agents.mdc` 作为专用规则文件。
- 该布局让 Claude、Codex 和 Cursor 读取同一组仓库规则与本地/共享 skills，同时把 workflow-only skills 从本地默认发现面中隔离出来。

## GitHub Copilot custom agents

- `.github/agents/` 存放随 AICodingFlow 模板交付的 GitHub Copilot custom agent profile。
- Custom agent profile 用于把已有产品知识或 workflow 能力暴露为 GitHub Copilot 可调用入口。
- GitHub Copilot custom agents 不替代 `.github/skills/` 中的 workflow skill 定义。
- `Product Wiki Query` agent 是面向产品知识库问答的 custom agent；查询应从 Product LLM Wiki index 进入相关 concept、summary 和 raw source。

## Windows symlink 规则

- `CLAUDE.md` 以及 `.claude`、`.codex` 和 `.cursor` 中的共享技能入口被记录在 Git 中。
- `CLAUDE.md` 与 Claude/Codex skills 入口依赖 tracked symlink。
- Windows clone 应优先启用真实 symlink checkout；禁用 symlink 时，Git 可能把共享入口检出为普通文本占位文件。
- 禁用 symlink 导致占位文件时，应重新启用 symlink 支持，移除占位文件，并从 Git 恢复 `CLAUDE.md`、`.claude/skills` 或 `.codex/skills` 等对应路径。
- 目录 junction 只适合作为无法使用真实 symlink 的本地 fallback，不是默认设置方式。

## Supporting Summaries

- [Agent 目录布局摘要](../summaries/agent-directory-layout.md)

## Related Concepts

- [项目安装脚本](project-installer.md)
- [Agent 与外层 workflow 职责边界](agent-workflow-boundaries.md)
- [Product Wiki Query agent](product-wiki-query-agent.md)
