---
type: summary
title: update-pr-review workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-05
review_due: 2026-09-03
sources:
  - docs/product/raw/update-pr-review-workflow.md
---

# update-pr-review workflow 摘要

Source: [docs/product/raw/update-pr-review-workflow.md](../../raw/update-pr-review-workflow.md)

`update-pr-review` workflow 从近期人类对 bot PR review 的反馈中学习稳定仓库偏好，并沉淀到 repo-local review companion guidance。它不处理单个 review 请求，不直接发布 review，也不改变 core review skill 的输出合同。

## 触发与输入

- 维护者通过 GitHub Actions `Update PR Review Guidance` workflow 手动运行。
- 默认扫描最近 14 天反馈；workflow inputs 可指定扫描天数、单个 PR、排除的 agent login，以及是否把非 agent bot 评论作为人类反馈纳入聚合。
- Agent comments 只能作为上下文，不能单独驱动规则更新。
- 规则学习必须来自 human review comments、human conversation comments 或 human-authored review bodies/comments。

## 规则学习

- Code review feedback 更新 `.github/skills/review-pr-repo/SKILL.md`。
- Spec review feedback 更新 `.github/skills/review-spec-repo/SKILL.md`。
- 证据不足、没有人类反馈或既有 guidance 已覆盖时，产出 `no_change`，不修改 companion guidance，也不创建更新 PR。
- 证据无法安全解释时，流程应产出错误，由外层 workflow 停止应用。

## 写入与 PR 边界

- Skill 只写临时 `update-pr-review-output/` 交接目录。
- 持久写入范围仅限 `.github/skills/review-pr-repo/` 和 `.github/skills/review-spec-repo/`。
- 不得修改 core review skills、workflow 文件、脚本、测试或产品代码，也不得改变 core review contract。
- 有 guidance diff 时，runner 使用固定分支 `feat/update-pr-review` 创建或更新 PR，并在 PR body 中包含来源输入摘要。
- 创建或更新 PR 只复用同一 head branch 上的 open PR；没有 guidance diff 时不创建 PR。

## 支持的概念

- [update-pr-review 自进化 review 规则 workflow](../concepts/update-pr-review-workflow.md)
