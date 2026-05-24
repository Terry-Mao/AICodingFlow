# 本地开发流

本地开发流适合开发者在自己的机器上与 Codex 协作完成常规改动：

```text
request -> issue -> branch/worktree -> commit -> push -> pr -> review -> merge
```

它的目标是让 issue、分支、提交和 PR 都可审查、可回滚、可复现。

## 使用前准备

在目标仓库安装 AICodingFlow：

```bash
./install.sh --target /path/to/target-repo
```

本地使用 GitHub 相关 SKILL 时，需要：

- 已安装并登录 `gh`。
- 当前仓库有可访问的 GitHub remote。
- Codex 能读取 `.agents/skills/`。

## 相关 SKILL

| SKILL | 用途 |
| --- | --- |
| `create-issue` | 根据当前对话或用户输入选择 `.github` issue 模板并创建 GitHub issue。 |
| `git-branch` | 根据 issue 或任务描述创建规范分支。 |
| `git-worktree` | 为并行 issue 或任务创建独立 worktree。 |
| `git-commit` | 从真实 diff 中整理原子提交。 |
| `git-push` | 安全推送分支，避免误推 base 分支或强推。 |
| `create-pr` | 创建或更新 GitHub PR。 |
| `diagnose-ci-failures` | 拉取 PR、branch 或 run 的 CI 失败日志并生成修复计划。 |
| `resolve-merge-conflicts` | 在 merge、rebase、cherry-pick 或 stash pop 冲突时提取并解决冲突。 |

## 典型用法

### 1. 创建 issue

```text
$create-issue
```

`create-issue` 会读取目标仓库的 `.github/ISSUE_TEMPLATE`，根据请求选择最合适的模板，保守填充 issue 标题和正文，并用 `gh issue create` 创建 issue。它默认不添加分类 labels；新 issue 打开后由 `triage-issue.yml` 自动应用 triage labels。

### 2. 创建分支

```text
$git-branch #47
```

`git-branch` 会读取 issue，推断 Conventional Commit 类型，生成 `<type>/<short-desc>-<issueID>` 格式的分支名，并从合适的 base 创建分支。

示例：

```text
docs/optimize-readme-47
```

### 3. 创建并行 worktree

```text
$git-worktree #48
```

`git-worktree` 会在 `.worktrees/<branch-name>` 下创建独立工作目录，适合同时处理多个 issue。它不会复制当前工作树里的未提交改动；Codex 后续 tool calls 会默认从新 worktree 运行，并输出你自己的 shell 需要执行的 `cd .worktrees/<branch-name>`。

### 4. 整理提交

```text
$git-commit
```

`git-commit` 会读取工作区状态、diff stat、完整 diff 和 staged diff，判断是否需要拆分提交，精确 stage 目标文件，并使用规范提交信息。

### 5. 推送分支

```text
$git-push
```

`git-push` 会检查当前分支、upstream 和待推送提交。没有 upstream 时执行 `git push -u origin <branch>`；已有 upstream 时执行普通 `git push`。它不会默认 force push，也会避免直接推送 `main`、`master`、`develop` 等共享 base 分支。

### 6. 创建或更新 PR

```text
$create-pr
```

`create-pr` 会检查 base diff，确认 base 分支已合入当前分支，生成包含 summary、validation 和 issue link 的 PR 描述。如果当前分支已有 PR，它会更新已有 PR，而不是重复创建。

## 本地 review

需要在本地模拟 GitHub PR Review 时，可以使用：

```text
$review-pr-local
$review-spec-local
```

它们会从当前分支准备 `pr_description.txt`、`pr_diff.txt` 和可选 `spec_context.md`，运行对应 review skill，并验证 `review.json`。本地 review 不会发布 GitHub 评论。

## 测试

AICodingFlow 本仓库的测试命令：

```bash
python3 -m unittest discover -s .github/tests
python3 -m unittest discover -s .github/aicodingflow-tests
```

修改 workflow、review 或 implementation 相关脚本后，建议额外编译检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile \
  .github/scripts/*.py \
  .agents/skills/implement-specs/scripts/*.py \
  .agents/skills/review-pr/scripts/validate_review_json.py \
  .agents/skills/update-pr-review/scripts/*.py
```
