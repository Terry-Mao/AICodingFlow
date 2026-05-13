# AICodingFlow

AICodingFlow 是一套面向 AI Coding 的工作流模板。它把本地 Codex SKILL、GitHub Actions、PR Review 自动化和 Spec 驱动开发串在一起，让一个 issue 从规划、实现、审查到合并都能有稳定、可复现的操作路径。

这个仓库主要提供两类能力：

- 本地操作 Git 的 SKILL：帮助开发者创建分支、整理提交、推送分支和创建 PR。
- GitHub Actions + Codex：在 CI 中装载 SKILL，自动创建 spec、审查 PR，并根据 review 反馈持续优化审查规则。

## 项目背景

AI Coding 最容易出问题的地方通常不是“能不能写代码”，而是流程不稳定：

- 分支命名不一致，issue 和实现脱节。
- commit 混杂，review 和回滚成本高。
- PR 描述缺少上下文，reviewer 需要重新追 issue。
- AI Review 使用实时 PR 状态，line number 和评论位置不稳定。
- spec、实现和 review 之间缺少明确交接。

AICodingFlow 的目标是把这些步骤标准化。它不追求替代开发者判断，而是把重复、容易出错的流程固化成可检查的 SKILL 和 workflow。

## 工作流概览

AICodingFlow 支持两条主线。

### 本地开发流

```text
issue -> branch -> commit -> push -> pr -> review -> CI -> merge
```

适合开发者在本地和 Codex 协作完成常规改动。

核心 SKILL：

- `git-branch`：根据 issue 创建规范分支。
- `git-commit`：从真实 diff 中整理原子提交。
- `git-push`：安全推送当前分支。
- `create-pr`：创建或更新 GitHub PR。

### Bot 协作流

```text
issue -> plan -> spec -> develop -> pr -> review -> comments -> merge
```

适合更复杂的任务，先把需求和技术方案写成 spec，再驱动实现和 review。

当前仓库覆盖两类 Bot 协作：

1. 从 issue 创建 spec 文档，提交 spec PR，PR Review 产生 inline/body 级别反馈，修复后合并。
2. 基于 issue 和已批准 spec 驱动实现，提交实现 PR，PR Review 对照 spec、diff 和仓库规则进行检查，修复后合并。

## 快速开始

克隆仓库并安装本地 SKILL：

```bash
git clone git@github.com:Terry-Mao/AICodingFlow.git
cd AICodingFlow

mkdir -p ~/.agents/skills
for skill in .agents/skills/*; do
  [ -d "$skill" ] || continue
  rsync -a "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

如果想先预览将会写入哪些文件：

```bash
for skill in .agents/skills/*; do
  [ -d "$skill" ] || continue
  rsync -ani "$skill/" "$HOME/.agents/skills/$(basename "$skill")/"
done
```

安装后，可以在 Codex 对话中直接点名 SKILL：

```text
$git-branch #47
$git-commit
$git-push
$create-pr
```

## 本地开发流

本地开发流围绕 `git-*` SKILL 展开，目标是让每一步都可审查、可回滚、可复现。

### 1. 创建分支

使用 `git-branch` 从 issue 创建分支：

```text
$git-branch #47
```

它会：

- 读取 issue 标题和正文。
- 推断 Conventional Commit 类型，例如 `feat`、`fix`、`docs`。
- 生成 `<type>/<short-desc>-<issueID>` 格式的分支名。
- 检查工作树是否干净、目标分支是否已存在、base 分支是否新鲜。

示例：

```text
docs/optimize-readme-47
```

### 2. 创建提交

使用 `git-commit` 整理提交：

```text
$git-commit
```

它会：

- 检查 `git status`、`git diff --stat`、完整 diff 和 staged diff。
- 判断变更是否应该拆分。
- 精确 stage 目标文件，避免误提交无关改动。
- 使用规范提交信息，例如 `feat(review): add spec context snapshots`。
- 在存在 native git hook 时走正常 `git commit` 流程，让 hook 自动运行。

### 3. 推送分支

使用 `git-push` 推送当前分支：

```text
$git-push
```

它会：

- 检查当前分支和远端。
- 避免直接推送 `main`、`master`、`develop` 等共享 base 分支。
- 没有 upstream 时执行 `git push -u origin <branch>`。
- 已有 upstream 时执行普通 `git push`。
- 遇到 rejected push 时不会默认 force push。

### 4. 创建或更新 PR

使用 `create-pr` 创建或更新 PR：

```text
$create-pr
```

它会：

- 检查 PR base diff。
- 确认 base 分支已经合入当前分支。
- 生成包含 summary、validation 和 issue link 的 PR 描述。
- 如果当前分支已有 PR，会更新而不是重复创建。
- 保留人工写入的 PR 内容，避免覆盖 reviewer 上下文。

## Bot 协作流

Bot 协作流用于更复杂或更需要规划的任务。它把“写 spec”和“实现代码”拆成可审查的阶段。

### 流程一：Issue 到 Spec PR

```text
issue -> plan -> product.md / tech.md -> spec PR -> review -> merge
```

对应 workflow：

```text
.github/workflows/create-spec-from-issue.yml
```

它会：

1. 读取 issue、labels、assignees、comments 和触发评论。
2. 准备稳定的 `issue_context.json` 和 `issue_comments.txt`。
3. 运行 spec 相关 SKILL：
   - `spec-driven-implementation`
   - `write-product-spec`
   - `create-product-spec`
   - `write-tech-spec`
   - `create-tech-spec`
4. 生成：

```text
specs/issue-<N>/product.md
specs/issue-<N>/tech.md
pr-metadata.json
```

5. 验证输出后推送 `spec/issue-<N>` 分支并创建或更新 spec PR。

Spec PR 只负责规划，不应该实现功能或修改生产代码。

### 流程二：Issue + Spec 到实现 PR

```text
issue + approved spec -> develop -> implementation PR -> AI review -> comments -> merge
```

实现阶段可以在本地完成，也可以由后续自动化 workflow 驱动。关键点是：实现 PR 的 review 会尽量带上已批准或仓库已有的 spec context。

AI PR Review 会：

- 生成稳定的 `pr_description.txt`。
- 生成带行号的 `pr_diff.txt`。
- 如果能找到相关 spec，生成 `spec_context.md`。
- 纯 `specs/` PR 使用 `review-spec-local`。
- 其他 PR 使用 `review-pr-local`。
- 如果 `spec_context.md` 存在，`review-pr` 会加载 `check-impl-against-spec`，把重要 spec drift 当成 review concern。
- 输出并验证 `review.json`。
- 通过 GitHub API 发布 PR review。

`spec_context.md` 的查找顺序：

1. 找到当前 PR 关联 issue。
2. 优先查找 `spec/issue-<N>` 分支上的 open PR，并要求带 `plan-approved` label。
3. 如果没有 approved spec PR，则从 PR base commit/ref 上读取 `specs/issue-<N>/product.md` 和 `tech.md`。
4. 如果都没有，就不生成 `spec_context.md`。

这保证 review 使用的 spec context 和 `pr_diff.txt` 的 base 语境一致，不会错误读取 implementation PR 自己的 head 内容。

## SKILL 一览

| SKILL | 用途 |
| --- | --- |
| `git-branch` | 根据 issue 或任务描述创建规范分支。 |
| `git-commit` | 从真实 diff 中整理原子提交。 |
| `git-push` | 安全推送分支，避免误推 base 分支或强推。 |
| `create-pr` | 创建或更新 GitHub PR。 |
| `write-product-spec` | 编写面向行为和验收标准的 product spec。 |
| `write-tech-spec` | 编写贴合当前代码结构的 technical spec。 |
| `create-product-spec` | GitHub issue 场景下的 product spec 包装器。 |
| `create-tech-spec` | GitHub issue 场景下的 tech spec 包装器。 |
| `spec-driven-implementation` | 组织 spec-first 的开发流程。 |
| `implement-specs` | 从已批准 spec 推进实现，并保持 spec 与实现一致。 |
| `review-pr` | 从稳定快照审查普通 PR，输出 `review.json`。 |
| `review-pr-local` | AICodingFlow 仓库的普通 PR review 包装器。 |
| `review-spec` | 审查纯 spec PR 的文档质量。 |
| `review-spec-local` | AICodingFlow 仓库的 spec review 包装器。 |
| `check-impl-against-spec` | 对照 `spec_context.md` 检查实现是否偏离 spec。 |
| `update-pr-review` | 从人工反馈中更新本仓库的 review companion SKILL。 |

## GitHub Actions

### AI PR Review

文件：

```text
.github/workflows/review-pr.yml
```

主要步骤：

1. checkout PR head。
2. 生成 `pr_description.txt`。
3. 生成 `pr_diff.txt`。
4. 根据 changed files 选择 review skill。
5. 按需生成 `spec_context.md`。
6. 运行 `openai/codex-action@v1`。
7. 验证 `review.json`。
8. 发布 GitHub PR review。
9. 上传 artifact。

需要配置：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `OPENAI_API_KEY` | Actions secret | Codex action 使用的 API key。 |
| `OPENAI_API_ENDPOINT` | Actions variable | Responses API endpoint，可填写 base URL 或 `/responses` URL。 |
| `GITHUB_TOKEN` | GitHub 内置 token | workflow 自动提供，用于发布 PR review。 |

Workflow 权限：

```yaml
permissions:
  contents: read
  pull-requests: write
```

### Create Spec From Issue

文件：

```text
.github/workflows/create-spec-from-issue.yml
```

这个 workflow 用于把 ready issue 转成 spec PR。它可以手动触发，也可以由 issue label、assignee 或 comment mention 触发。

需要配置：

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `SPEC_AGENT_LOGIN` | Actions variable | 被分配或 mention 时触发 spec 创建的 agent 登录名。 |
| `OPENAI_API_KEY` | Actions secret | Codex action 使用的 API key。 |
| `OPENAI_API_ENDPOINT` | Actions variable | Responses API endpoint。 |

### Update PR Review

文件：

```text
.github/workflows/update-pr-review.yml
```

这个 workflow 聚合人工对 bot review 的反馈，并更新：

```text
.agents/skills/review-pr-local/SKILL.md
.agents/skills/review-spec-local/SKILL.md
```

它只允许写 repo-local companion skill，不允许修改核心 review contract。

## 目录结构

```text
.agents/skills/                  # Codex SKILL
.github/workflows/               # GitHub Actions workflow
.github/scripts/                 # workflow 使用的 Python helper
specs/                           # issue 对应的 product/tech spec
tests/                           # Python unittest 测试
```

常用脚本：

| 脚本 | 用途 |
| --- | --- |
| `build_pr_diff.py` | 把 git diff 转成稳定的 `PR_DIFF_V1`。 |
| `write_pr_description.py` | 从 GitHub event 写出 PR 描述快照。 |
| `select_review_skill.py` | 根据 changed files 选择 review skill。 |
| `write_spec_context.py` | 为实现 PR 解析并格式化 spec context。 |
| `post_pr_review.py` | 把 `review.json` 发布成 GitHub PR review。 |
| `prepare_issue_spec_context.py` | 为 spec 生成准备稳定 issue context。 |
| `validate_spec_output.py` | 校验 spec workflow 输出。 |
| `validate_review_json.py` | 校验 AI review 输出结构和 inline 目标。 |

## 在其他仓库中使用

复制 `.agents/` 和 `.github/`：

```bash
rsync -a .agents/ /path/to/target-repo/.agents/
rsync -a .github/ /path/to/target-repo/.github/
```

然后在目标仓库中：

1. 提交复制后的文件。
2. 配置 `OPENAI_API_KEY` 和 `OPENAI_API_ENDPOINT`。
3. 如果启用 spec workflow，配置 `SPEC_AGENT_LOGIN`。
4. 根据目标仓库调整 `review-pr-local` 和 `review-spec-local` 的 repo-specific guidance。

## 本地开发与测试

运行全部测试：

```bash
python3 -m unittest discover -s tests
```

建议在修改 workflow 或 review 相关脚本后额外检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile \
  .github/scripts/*.py \
  .agents/skills/review-pr/scripts/validate_review_json.py \
  .agents/skills/update-pr-review/scripts/*.py
```

如果修改 GitHub Actions，也应确认 YAML 能被解析。

## 设计原则

- 先稳定上下文，再让 AI 工作：PR review 使用 `pr_description.txt`、`pr_diff.txt` 和可选 `spec_context.md`。
- 控制逻辑使用结构化数据，给 agent 阅读时再格式化成 markdown。
- 本地 SKILL 不应该做危险操作，例如默认 force push、广泛 staging 或删除用户文件。
- CI 中的 review skill 不直接调用 GitHub API，不发布评论，只写 `review.json`。
- repo-local companion 可以补充审查偏好，但不能覆盖核心 schema、severity、diff-line targeting 和 validator 规则。

## 反馈与问题排查

如果遇到问题，请在 issue 或 PR 中提供：

- 你正在运行的 SKILL 或 workflow。
- 分支名、issue number、PR 链接。
- 相关命令输出或 GitHub Actions 日志。
- 对 PR review 问题，尽量附上 artifact：

```text
pr_description.txt
pr_diff.txt
spec_context.md
review.json
```

这些快照能帮助复现 line number、inline comment 和 spec context 相关问题。
