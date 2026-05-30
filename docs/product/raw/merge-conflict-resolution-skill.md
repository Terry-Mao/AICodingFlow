# Merge conflict resolution skill

`resolve-merge-conflicts` skill 用于帮助 agent 在 merge、rebase、cherry-pick 或
stash pop 因 Git 冲突停止后，先提取紧凑的冲突上下文，再逐个文件完成冲突解决。它的目标是减少
无差别读取完整文件的上下文成本，同时保留足够的信息判断 `ours`、`theirs` 与必要的合并内容。

## 适用入口

当 Git 操作产生 unmerged paths，或工作区文件包含 `<<<<<<<`、`=======`、
`>>>>>>>` 等冲突标记时，可以使用该 skill。Agent 应先运行冲突摘要命令，确认 unresolved
文件、index stages 和每个文件的文本冲突 hunk 数量，再按单个文件展开详细上下文。

详细查看某个文件时，skill 优先使用辅助脚本输出冲突标记附近的上下文、`ours`、`base`、
`theirs` 片段，以及 `ours` 与 `theirs` 的紧凑 unified diff。只有这些紧凑输出不足以判断正确
合并时，才读取更大范围或完整文件。

## 冲突类型与输出

辅助脚本会汇总 Git index 中的 unresolved entries，并识别 marker-based text conflicts
以及没有工作区标记的 index-only conflicts，例如 add/add、deleted-by-us、deleted-by-them
或一般 unmerged 状态。

脚本支持 summary、单文件详情、全部文件详情、JSON 输出和输出大小控制。对二进制或无法作为
UTF-8 文本可靠展示的 stage 内容，脚本不会把内容当作普通文本 diff 展开，而是保守地回退到可用
的 stage 信息或预览。

## 解决与验证边界

Agent 应一次处理一个冲突文件。可以在明确合适时选择 `ours` 或 `theirs` 一侧，也可以编辑文件
移除冲突标记并保留合并后的内容。完成后必须重新检查 unresolved files，确认没有残留冲突标记，
并运行与改动范围相关的测试、构建或 lint。

该 skill 是本地冲突解决辅助能力。它不会自动决定业务语义，不会跳过用户工作区安全检查，也不负责
提交、推送、创建 PR 或修改 GitHub issue/PR。解决完成后是否 stage resolved files 取决于正在
执行的上层 Git 操作或用户请求。

来源：PR #114，Issue #113。
