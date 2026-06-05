---
type: concept
title: update-pr-review 自进化 review 规则 workflow
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/update-pr-review-workflow.md
---

# update-pr-review 自进化 review 规则 workflow

`update-pr-review` workflow 从近期人类对 bot PR review 的反馈中学习稳定仓库偏好，并把这些偏好写入 repo-local review companion guidance。它不处理单个 review 请求，不直接发布 review，也不改变 core review skill 的输出合同。

## 输入信号

- 维护者通过 `Update PR Review Guidance` workflow 手动运行。
- 默认扫描最近 14 天反馈；inputs 可指定扫描天数、单个 PR、排除的 agent login，以及是否把非 agent bot 评论作为人类反馈。
- Agent comments 只能作为上下文，不能单独驱动规则更新。
- 有效学习信号来自 human review comments、human conversation comments 或 human-authored review bodies/comments。

## 学习与路由

- Code review feedback 更新 `.agents/skills/review-pr-repo/SKILL.md`。
- Spec review feedback 更新 `.agents/skills/review-spec-repo/SKILL.md`。
- 证据不足、没有人类反馈或已有 guidance 覆盖时，输出 `no_change`。
- 证据无法安全解释时，流程应输出错误并由外层 workflow 停止应用。

## 写入边界

- Skill 只写临时 `update-pr-review-output/` 交接目录。
- 持久写入范围仅限 `.agents/skills/review-pr-repo/` 和 `.agents/skills/review-spec-repo/`。
- 不得修改 core review skills、workflow 文件、脚本、测试或产品代码。
- 不得改变 core review contract，包括输出 schema、severity labels、diff-line targeting、snapshot rules、validation rules 或 safety rules。

## PR 行为

- 有 guidance diff 时，runner 使用固定分支 `feat/update-pr-review` 创建或更新 PR。
- PR body 包含来源输入摘要。
- 创建或更新 PR 只复用同一 head branch 上的 open PR。
- 没有 guidance diff 时不创建 PR。

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [安全补充 review](security-review-supplements.md)

## Supporting Summaries

- [update-pr-review workflow 摘要](../summaries/update-pr-review-workflow.md)
