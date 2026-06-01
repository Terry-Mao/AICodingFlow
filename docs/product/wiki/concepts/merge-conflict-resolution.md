---
type: concept
title: Merge conflict resolution
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-06-01
review_due: 2026-08-30
sources:
  - docs/product/raw/merge-conflict-resolution-skill.md
---

# Merge conflict resolution

Merge conflict resolution 是本地冲突处理辅助能力，用于在 Git 操作停止后提取紧凑上下文并逐文件解决冲突。

## 当前规则

- 适用于 merge、rebase、cherry-pick 或 stash pop 产生 unresolved paths 的情况。
- 工作区出现 `<<<<<<<`、`=======`、`>>>>>>>` 标记时也适用。
- agent 应先运行摘要命令，确认 unresolved 文件、index stages 和文本冲突 hunk 数量。
- 单文件详情优先使用辅助脚本的紧凑上下文、`ours` / `base` / `theirs` 片段和紧凑 diff。
- 只有紧凑输出不足时才读取更大范围或完整文件。
- 支持 marker-based text conflicts 和 index-only conflicts。

## 边界

- 一次处理一个冲突文件。
- 完成后重新检查 unresolved files 和残留冲突标记。
- 运行与改动范围相关的测试、构建或 lint。
- skill 不自动决定业务语义，不负责提交、推送、创建 PR 或修改 GitHub issue/PR。

## Supporting Summaries

- [Merge conflict resolution skill 摘要](../summaries/merge-conflict-resolution-skill.md)

## Related Concepts

- [本地 Git helper skills](local-git-helper-skills.md)

