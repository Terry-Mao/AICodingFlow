# Agent 目录布局

AICodingFlow 使用根目录 `AGENTS.md` 作为共享仓库级 agent guidance，并使用 `.agents/`
保存本地开发与共享 skills，使用 `.github/skills/` 保存 GitHub workflow 专用 skills。这样多个工具可以读取同一份仓库指导、skills 和工具规则，避免在
`.claude`、`.codex`、`.cursor` 等目录中维护重复内容。

## 共享入口

仓库根目录提供工具期望的入口，并按工具需要引用共享 guidance 或 `.agents/` 中的共享内容：

- `AGENTS.md` 是 Codex 默认加载的仓库级 agent guidance 权威入口。
- `CLAUDE.md -> AGENTS.md` 让 Claude Code 加载同一份仓库级 guidance。
- `.claude/skills -> ../.agents/skills`
- `.codex/skills -> ../.agents/skills`
- `.cursor/rules/agents.mdc` 是 Cursor 专用规则文件。

`.agents/skills/` 存放本地开发和共享 skills，并通过 `.claude/skills`、`.codex/skills`
暴露给本地工具默认发现。`.github/skills/` 存放 GitHub Actions workflow-only skills，
由 workflow prompt 显式读取，不作为本地默认 skill 入口。`.agents/contracts/` 存放 skills 与
workflows 共享的稳定 artifact schema、validator contract 和 workflow/skill 边界合同。
Cursor 规则通过 `.cursor/rules/agents.mdc` 暴露给 Cursor。

该布局的产品目标是让 Claude、Codex 和 Cursor 使用同一组仓库规则与本地/共享 skills，同时把
GitHub workflow-only skills 从本地默认发现面中隔离出来。

## GitHub Copilot custom agents

`.github/agents/` 存放随 AICodingFlow 模板交付的 GitHub Copilot custom agent profile。该目录用于把
已有产品知识或 workflow 能力暴露为 GitHub Copilot 可调用的 agent 入口，而不是替代
`.github/skills/` 中的 workflow skill 定义。

`Product Wiki Query` agent 是面向产品知识库问答的 GitHub Copilot custom agent。它基于
`.github/skills/product-wiki/SKILL.md` 中的 Query、Staged Review、Style 和查询相关规则回答
AICodingFlow 产品行为、workflow、边界、状态和规则问题。查询应从 `docs/product/wiki/index.md`
进入相关 concept、summary 和 raw source；当 wiki 与 raw source 冲突时，以 `docs/product/raw/`
中的权威产品事实为准。

## Windows symlink 支持

仓库把 `CLAUDE.md` 以及 `.claude`、`.codex` 和 `.cursor` 中的共享技能入口记录在 Git 中，
其中 `CLAUDE.md` 与 Claude/Codex skills 入口使用 symlink 指向共享内容。Windows 环境应优先
启用 Git 的真实 symlink checkout，例如在 clone 前设置 `core.symlinks=true`，并确保系统允许创建 symlink。

如果 Windows clone 时禁用了 symlink，Git 可能把 `CLAUDE.md`、`.claude/skills` 或
`.codex/skills` 检出为普通文本文件。修复方式是重新启用 symlink 支持，移除这些占位文件，
并从 Git 恢复对应路径。

目录 junction 只适合作为无法使用真实 symlink 的本地 fallback。它们不是 tracked symlink 路径的默认设置方式，因为可能让 working tree 与 Git index 表现不一致。

来源：PR #159，Issue #156；PR #161；PR #175；PR #204，Issue #202；PR #246；Issue #266。
