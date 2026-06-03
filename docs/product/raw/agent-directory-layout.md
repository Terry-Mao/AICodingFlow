# Agent 目录布局

AICodingFlow 使用 `.agents/` 作为共享 agent 配置目录，并为不同 AI coding 工具提供它们期望的本地入口。这样多个工具可以读取同一份仓库指导、skills 和工具规则，避免在 `.claude`、`.codex`、`.cursor` 等目录中维护重复内容。

## 共享入口

仓库根目录中的工具入口是普通目录，目录内部按工具需要引用 `.agents/` 中的共享内容：

- `.claude/CLAUDE.md -> ../.agents/AGENTS.md`
- `.claude/skills -> ../.agents/skills`
- `.codex/AGENTS.md -> ../.agents/AGENTS.md`
- `.codex/skills -> ../.agents/skills`
- `.cursor/rules/agents.mdc` 是 Cursor 专用规则文件。

`.agents/AGENTS.md` 是仓库级 agent guidance 的权威入口。`.agents/skills/` 存放可复用 workflow skills；Cursor 规则通过 `.cursor/rules/agents.mdc` 暴露给 Cursor。

该布局的产品目标是让 Claude、Codex 和 Cursor 使用同一组仓库规则与 workflow skills，而不是为每个工具维护独立配置副本。

## Windows symlink 支持

仓库把 `.claude`、`.codex` 和 `.cursor` 作为普通目录记录在 Git 中，目录内的 Claude 和 Codex 入口使用 symlink 指向 `.agents/` 中的共享文件。Windows 环境应优先启用 Git 的真实 symlink checkout，例如在 clone 前设置 `core.symlinks=true`，并确保系统允许创建 symlink。

如果 Windows clone 时禁用了 symlink，Git 可能把 `.claude/skills`、`.claude/CLAUDE.md`、`.codex/skills` 或 `.codex/AGENTS.md` 检出为普通文本文件。修复方式是重新启用 symlink 支持，移除这些占位文件，并从 Git 恢复 `.claude` 和 `.codex`。

目录 junction 只适合作为无法使用真实 symlink 的本地 fallback。它们不是 tracked symlink 路径的默认设置方式，因为可能让 working tree 与 Git index 表现不一致。

来源：PR #159，Issue #156；PR #161。
