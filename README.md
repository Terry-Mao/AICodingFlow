# AICodingFlow

AICodingFlow 是一套面向 AI Coding 的工作流模板。它把本地 Codex SKILL、GitHub Actions、PR Review 自动化、Issue Triage 和 Spec 驱动开发串在一起，让一个 issue 从规划、实现、审查到合并都有稳定、可复现的操作路径。

这个仓库提供两类能力：

- 本地开发流：用 `create-issue`、`git-*` 和 `create-pr` SKILL 规范 issue 创建、分支、提交、推送和 PR 创建。
- GitHub 协作流：用 GitHub Actions + Codex 从 issue 创建 spec、实现 issue、审查 PR、响应 review comments，并从人工反馈中更新仓库本地规则。

## Quick Start

一行安装到目标项目：

```bash
curl -fsSL https://raw.githubusercontent.com/Terry-Mao/AICodingFlow/main/install.sh | bash -s -- --target /path/to/target-repo
```

也可以先克隆本仓库再安装：

```bash
git clone git@github.com:Terry-Mao/AICodingFlow.git
cd AICodingFlow

./install.sh --target /path/to/target-repo
```

预览将写入的文件：

```bash
./install.sh --target /path/to/target-repo --dry-run
```

安装脚本依赖 `bash`、`git`、`rsync`；使用一行安装命令时还需要 `curl`。它会同步 `.agents/skills/`、`.github/scripts/`、`.github/aicodingflow-tests/` 和受管 workflow，不会同步 AICodingFlow 仓库自用的 `.github/tests/` 与 `.github/workflows/ci.yml`。

安装后，在目标仓库配置：

| 名称 | 类型 | 用途 |
| --- | --- | --- |
| `OPENAI_API_KEY` | Actions secret | Codex action 使用的 API key。 |
| `OPENAI_API_ENDPOINT` | Actions variable | Responses API endpoint，可以是 base URL 或 `/responses` URL。 |
| `AGENT_LOGIN` | Actions variable | GitHub issue / PR comment 中被分配或 mention 的 agent 登录名。 |
| `REVIEW_BOT_LOGIN` | Actions variable | 可选。发布 PR review 的 bot 登录名；默认 `github-actions[bot]`。如果 review workflow 改用其他 token / bot 账号发 review，需要设置为实际 review 作者，用于后续 `APPROVE` 清理旧的 bot `REQUEST_CHANGES`。 |
| `APP_CLIENT_ID` | Actions variable | GitHub App client ID；implementation/comment fix 需要更新 workflow 文件时使用。 |
| `APP_PRIVATE_KEY` | Actions secret | GitHub App private key；App 需要 `Contents: Read and write` 和 `Workflows: Read and write`。 |

如果目标项目首次接入 issue triage 自动化，可以让 Codex 运行：

```text
$bootstrap-issue-config
```

它会分析已有 labels、issues 和 contributors，生成或更新 `.github/issue-triage/config.json` 与 `.github/CODEOWNERS`。

## 工作流概览

### 本地开发流

```text
issue -> branch/worktree -> commit -> push -> pr -> review -> merge
```

开发者在本地与 Codex 协作完成常规改动。常用 SKILL：

- `create-issue`：根据对话上下文或用户输入，选择 `.github` issue 模板并创建 GitHub issue。
- `git-branch`：根据 issue 或任务创建规范分支。
- `git-worktree`：为并行任务创建独立 worktree。
- `git-commit`：从真实 diff 中整理原子提交。
- `git-push`：安全推送当前分支。
- `create-pr`：创建或更新 GitHub PR。

详细说明见 [本地开发流](docs/local-development-flow.md)。

### GitHub 协作流

```text
issue -> triage/spec -> implement -> pr -> review -> comments -> merge
```

更复杂的任务可以通过 GitHub labels、assignees、mentions 和 PR comments 驱动：

- `triage-issue.yml`：分析新 issue，应用分类 labels，发布 triage summary。
- `create-spec-from-issue.yml`：把 `ready-to-spec` issue 转成 `specs/issue-<N>/product.md` 和 `tech.md`。
- `plan-approved.yml`：批准 spec PR 后同步 issue 状态，并在满足实现 gate 时调度 implementation。
- `create-implementation-from-issue.yml`：把 `ready-to-implement` issue 交给 Codex 实现。
- `review-pr.yml`：基于稳定快照审查 PR。
- `respond-to-pr-comment.yml`：通过 `@AGENT_LOGIN /fix` 响应 PR conversation、review 或 inline comments。
- `update-pr-review.yml` / `update-dedupe.yml`：从人工反馈中更新仓库本地 companion SKILL。

详细说明见 [GitHub 协作流](docs/github-collaboration-flow.md) 和 [自进化 repo SKILL](docs/evolving-repo-skills.md)。

## 目录结构

```text
.agents/                         # 多工具共享的 agent 配置入口
.agents/skills/                  # Codex SKILL
.codex/                          # Codex 入口目录
.claude/                         # Claude 入口目录
.cursor/rules/                   # Cursor rules
.github/workflows/               # GitHub Actions workflow
.github/scripts/                 # workflow 使用的 Python helper
.github/aicodingflow-tests/      # 随安装脚本交付的 workflow/script unittest 和 fixtures
.github/tests/                   # AICodingFlow 本仓库自用 unittest
.github/issue-triage/            # issue triage 配置
docs/                            # 详细文档
specs/                           # issue 对应的 product / tech spec
```

工具入口目录 `.claude`、`.codex`、`.cursor` 是普通目录，内部按工具需要引用 `.agents` 的共享内容。更多说明见 [Agent Directories](docs/agent-directories.md)。

## 贡献和反馈

欢迎通过 issue 或 PR 反馈问题。提交 bug 时，请尽量包含：

- 正在运行的 SKILL 或 workflow。
- 分支名、issue number、PR 链接。
- 相关命令输出或 GitHub Actions 日志。
- PR review 问题的 artifact：`pr_description.txt`、`pr_diff.txt`、`spec_context.md`、`review.json`。
- implementation / comment fix 问题的 artifact：`issue_context.json`、`pr_comment_context.json`、`spec_context.md`、`implementation_summary.md`、`pr-metadata.json`、`validation-error.txt`。

本仓库测试命令：

```bash
python3 -m unittest discover -s .github/tests
python3 -m unittest discover -s .github/aicodingflow-tests
```
