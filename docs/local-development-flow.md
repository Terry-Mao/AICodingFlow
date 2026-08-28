# 本地开发流

本地开发流用于让 Codex 在开发者机器上完成可审查、可回滚的常规改动：

```text
request -> issue -> branch/worktree -> commit -> push -> pr -> review -> merge
```

## 准备

在目标仓库安装 AICodingFlow：

```bash
./install.sh --target /path/to/target-repo
```

使用 GitHub 相关 SKILL 还需要已登录的 `gh`、可访问的 GitHub remote，
以及可读取的 `.agents/skills/`。

## SKILL 入口

| 阶段 | SKILL | 作用 |
| --- | --- | --- |
| Issue | `create-issue` | 按仓库模板创建安全、可分诊的 issue。 |
| 分支 | `git-branch` | 创建规范分支并选择安全 base。 |
| 并行开发 | `git-worktree` | 创建隔离 worktree，不带入未提交改动。 |
| 提交 | `git-commit` | 从真实 diff 整理原子 commit。 |
| 发布 | `git-push` | 推送当前分支，避免误推共享分支或强推。 |
| PR | `create-pr` | 创建或更新当前分支的 open PR。 |
| 诊断 | `diagnose-ci-failures` | 提取 CI 失败上下文并生成修复计划。 |
| 冲突 | `resolve-merge-conflicts` | 在 Git 冲突时提取上下文并完成解决。 |

## 常用调用

```text
$create-issue       # 需要把请求落成 GitHub issue 时
$git-branch #47      # 单分支开发
$git-worktree #48    # 并行任务
$git-commit
$git-push
$create-pr
```

各 SKILL 会自行检查当前状态、模板、base、diff 和远端；只在结果可能受
影响时增加检查。使用 `git-worktree` 后，后续 agent 操作默认在新目录中，
用户自己的 shell 仍需执行它报告的 `cd` 命令。

## 本地 review

开发完成但尚未创建 PR 时，可运行：

```text
$review-pr-local
$review-spec-local
```

它们把快照和 `review.json` 放到系统临时目录，按对应 review SKILL 验证，
不会发布 GitHub 评论。

## 验证

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/tests
git diff --check
```

修改 Python workflow/script 时，再运行：

```bash
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile \
  .github/scripts/*.py \
  .github/skills/implement-specs/scripts/*.py \
  .github/skills/review-pr/scripts/validate_review_json.py \
  .github/skills/update-pr-review/scripts/*.py
```
