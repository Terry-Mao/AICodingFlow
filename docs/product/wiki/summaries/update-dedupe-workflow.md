---
type: summary
title: update-dedupe workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-02
review_due: 2026-08-31
sources:
  - docs/product/raw/update-dedupe-workflow.md
---

# update-dedupe workflow 摘要

Source: [docs/product/raw/update-dedupe-workflow.md](../../raw/update-dedupe-workflow.md)

`update-dedupe` workflow 从维护者近期正式关闭为 duplicate 的 issues 中学习稳定重复模式，并把这些模式沉淀到 repo-local dedupe companion guidance。它不处理单个新 issue，不直接修改 GitHub issues，也不改变 core `dedupe-issue` 的判重合同。

## 触发与输入

- 维护者通过 GitHub Actions `Update Dedupe Guidance` workflow 手动运行。
- 默认检查最近 7 天的 duplicate 关闭记录。
- workflow inputs 可以覆盖目标 repo、扫描天数，以及是否真正推送更新分支。
- 聚合脚本只使用强 duplicate 信号：issue 的 `state_reason` 必须是 `duplicate`，timeline 中必须存在可解析 canonical issue 的 `marked_as_duplicate` 事件。
- 普通评论、标题相似、agent 推断、单个候选匹配或缺少 canonical timeline 事件的记录不能单独触发规则学习。

## 规则学习

- `update-dedupe` skill 读取聚合后的 duplicate feedback JSON。
- 只有存在 repeated cluster 时才提出 guidance 更新。
- repeated cluster 表示至少两个独立 issues 被维护者关闭为同一个 canonical issue 的 duplicate，或存在同等强度的维护者结构化证据。
- 证据不足、没有 repeated cluster，或现有 guidance 已覆盖该模式时，流程产出 `no_change`。
- 证据存在但无法安全解释时，流程应产出错误，由外层 workflow 停止应用。

## 写入与 PR 边界

- skill 本身只写临时 `update-dedupe-output/` 交接目录。
- 需要更新 guidance 时，输出 `.agents/skills/dedupe-issue-repo/SKILL.md` 的完整 replacement 内容。
- 持久写入范围仅限 `.agents/skills/dedupe-issue-repo/`。
- 不得修改 `.agents/skills/dedupe-issue/SKILL.md`，也不得放宽 2-candidate minimum、similarity threshold、输出 schema、候选来源或 precision-over-recall 原则。
- 有 guidance diff 时，runner 使用固定分支 `feat/update-dedupe` 创建或更新 PR，并在 PR body 中包含 evidence summary。
- 没有 guidance diff 时，不创建 PR。

## 支持的概念

- [update-dedupe 自进化规则 workflow](../concepts/update-dedupe-workflow.md)
- [Repo-specific duplicate guidance](../concepts/repo-specific-duplicate-guidance.md)
