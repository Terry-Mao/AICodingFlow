---
type: summary
title: update-triage workflow 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-10
review_due: 2026-09-08
sources:
  - docs/product/raw/update-triage-workflow.md
---

# update-triage workflow 摘要

Source: [docs/product/raw/update-triage-workflow.md](../../raw/update-triage-workflow.md)

`update-triage` workflow 从最近被 issue triage 处理过的 issues 中收集维护者后续修正信号，并把稳定、重复、仓库特定的 triage 经验沉淀到 repo-local triage companion guidance。它不重新分诊单个 issue，不直接修改 GitHub issues，也不改变 core `triage-issue` skill 的输出合同或安全边界。

## 触发与输入

- 维护者通过 GitHub Actions `Update Triage Guidance` workflow 手动运行。
- 默认分析最近 7 天内有更新、且能可靠定位 bot triage 时间的 issues。
- Workflow inputs 可覆盖扫描天数、指定单个 issue 用于调试，并控制是否推送更新分支。
- 聚合脚本先定位 `triaged_at`：优先使用 bot triage comment marker 的创建时间，其次使用 bot 添加 `triaged` label 的 timeline event。
- 无法可靠定位 triage 时间的 issue 会被跳过，避免学习 triage 前的维护者动作。
- 只收集 `created_at > triaged_at` 的维护者 label added / removed、reopened 事件和后续评论。
- 维护者身份优先来自 GitHub 返回的 `OWNER`、`MEMBER` 或 `COLLABORATOR`；必要时可使用可验证组织成员身份作为 fallback。
- Bot actor 和普通 reporter 评论默认不作为学习信号；正式 duplicate 关闭信号由 `update-dedupe` 负责。

## 规则学习

- `update-triage` skill 读取聚合后的 triage feedback JSON，寻找稳定、重复、可泛化的维护者修正模式。
- 默认至少需要两个独立 issues 支持同一模式，才认为证据足够。
- 可学习模式包括维护者反复纠正的 label 分类、area 判断、issue shape heuristic、复现度默认值或同类 follow-up question。
- 证据不足、只有一次性 override、现有 guidance 已覆盖，或全部信号属于 duplicate 学习范围时，流程产出 `no_change`。
- 证据存在但无法安全解释时，流程产出 `error`，由外层 workflow 停止应用。

## 写入与 PR 边界

- Skill 本身只写临时 `update-triage-output/` 交接目录。
- 需要更新 guidance 时，skill 输出完整 replacement file，外层 runner 负责应用输出、校验写入范围、提交、推送以及创建或更新 PR。
- 持久写入范围仅限 `.github/skills/triage-issue-repo/SKILL.md` 和 `.github/issue-triage/config.json`。
- 普通 triage heuristic 应写入 `.github/skills/triage-issue-repo/SKILL.md`。
- 只有稳定模式表明 label taxonomy 需要新增 label、重命名 label 或澄清 description 时，才允许最小化更新 `.github/issue-triage/config.json`。
- 流程不得修改 core `triage-issue` skill、`dedupe-issue-repo` companion、workflow 文件、脚本、测试、README 或产品代码。
- 有 guidance diff 时，runner 使用固定分支 `feat/update-triage` 创建或更新 PR；没有 guidance diff 时不创建 PR。
- PR body 说明数据来源窗口或指定 issue、学到的维护者修正模式摘要、更新文件，以及非关闭 issue reference。

## 支持的概念

- [update-triage 自进化 triage 规则 workflow](../concepts/update-triage-workflow.md)
- [Issue triage workflow](../concepts/issue-triage-workflow.md)
- [Issue triage 结果契约](../concepts/issue-triage-result-contract.md)
