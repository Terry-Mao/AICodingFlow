---
type: summary
title: Merge conflict resolution skill 摘要
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/merge-conflict-resolution-skill.md
---

# Merge conflict resolution skill 摘要

Source: [docs/product/raw/merge-conflict-resolution-skill.md](../../raw/merge-conflict-resolution-skill.md)

`resolve-merge-conflicts` skill 帮助 agent 在 merge、rebase、cherry-pick 或 stash pop 因 Git 冲突停止后，先提取紧凑冲突上下文，再逐个文件完成冲突解决。

## 适用入口

- Git 操作产生 unmerged paths 时使用。
- 工作区文件包含 `<<<<<<<`、`=======`、`>>>>>>>` 等冲突标记时使用。
- agent 应先运行冲突摘要命令，确认 unresolved 文件、index stages 和每个文件的文本冲突 hunk 数量。
- 展开单文件详情时，优先使用辅助脚本输出冲突标记附近上下文、`ours`、`base`、`theirs` 片段，以及 `ours` 与 `theirs` 的紧凑 unified diff。
- 只有紧凑输出不足以判断正确合并时，才读取更大范围或完整文件。

## 冲突类型与输出

- 辅助脚本汇总 Git index unresolved entries。
- 识别 marker-based text conflicts。
- 识别没有工作区标记的 index-only conflicts，例如 add/add、deleted-by-us、deleted-by-them 或一般 unmerged 状态。
- 支持 summary、单文件详情、全部文件详情、JSON 输出和输出大小控制。
- 对二进制或无法可靠展示为 UTF-8 文本的 stage 内容，脚本保守回退到可用 stage 信息或预览。

## 解决与验证边界

- agent 应一次处理一个冲突文件。
- 可以在明确合适时选择 `ours` 或 `theirs`，也可以编辑文件保留合并后内容。
- 完成后必须重新检查 unresolved files，确认没有残留冲突标记，并运行相关测试、构建或 lint。
- skill 不自动决定业务语义，不跳过用户工作区安全检查，不负责提交、推送、创建 PR 或修改 GitHub issue/PR。
- 是否 stage resolved files 取决于正在执行的上层 Git 操作或用户请求。

## 支持的概念

- [Merge conflict resolution](../concepts/merge-conflict-resolution.md)
- [本地 Git helper skills](../concepts/local-git-helper-skills.md)

