# 产品规格：PR 审查流程一期

## Summary

让贡献者在 PR 中说明测试、风险和回滚方式；让 AI 审查在作者跨多次提交修复时减少重复意见。

## Problem

目前单次 AI Review 无法区分同一 PR 的修复轮次。重复触发 Action 可能重复发布意见，PR 信息也缺少统一要求。

## Goals

1. PR 正文具备 Summary、Testing、Risk、How to revert 四部分，内容不能为空。
2. 一次 Action 只执行一次 Review；轮次跨 Action、按已审查的不同 PR base/head SHA 快照计算。
3. 第四轮起重点审查上次已审查提交以来的增量，并评估反复局部修复是否暴露整体方案问题。

## Non-goals

一期不引入 PR 多 Agent 共识或风险分级审批；它们是后续阶段。夜间存量扫描暂不实施，待产品规则明确后再设计。原生 merge queue 等仓库迁至符合条件的组织后启用。

## User experience

1. PR 模板和自动创建 PR 的指南要求填写四部分；自动实现与 spec PR 的元数据缺少任一部分时，创建 PR 前校验失败。CI 在 PR 新建、修改正文及推送后检查所有 PR 的正文；自动生成的文档与指南 PR 也补齐四部分。
2. 同一 base/head SHA 快照的 Action 重跑不增加轮次，且在调用 AI 前直接跳过。作者推送新 commit，或 base SHA 改变后，下一次成功发布的 Review 形成下一轮。
3. 前三轮看完整 PR。第四轮起，如果历史 head 可追溯且 base 未改变，关注从上次已审查 head 至当前 head 的增量；否则回退完整审查。未解决的旧意见仍需检查，inline 定位仍以当前完整 PR diff 为准。
4. 审查意见需指出同类缺陷的排查边界。仅涉及风格、诊断日志或微小清理的意见不发布；既有 Bug 不归咎于本次 PR。

## Success criteria

- 测试 PR 连续修复三次后，第四次 Review 可以看到正确轮次和增量范围。
- 同一 base/head SHA 快照重跑不新增重复 Bot Review；base 变化时同一 head 可重新审查。

## Validation

运行对应单测、完整仓库单测、Python 编译检查、`actionlint` 与 `git diff --check`；在测试 PR 上验证跨 Action 轮次。

## Open questions

后续多 Agent 共识的运行成本、风险审批的维护者人数和组织仓库迁移时间，进入各自阶段前另行确认。
