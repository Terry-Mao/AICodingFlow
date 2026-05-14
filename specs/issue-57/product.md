# 产品规格：`plan-approved` 移除 `ready-to-spec` 并优化 workflow 执行顺序

## 1. Summary

本功能明确并自动化 spec-first issue 的生命周期推进规则：当维护者在 linked spec PR 上添加 `plan-approved` 后，系统应把该 spec PR 的内容视为可用于后续实现的 authoritative spec context，并自动从 linked issue 移除 `ready-to-spec`。

期望结果是：spec 审批、issue 状态同步、以及 implementation workflow 的触发顺序可预测。`plan-approved` 只表示“spec 内容已批准可作为实现依据”，不会自动给 issue 添加 `ready-to-implement`；implementation 只有在 issue 已经带有 `ready-to-implement` 且 bot 已分配时才会启动。

## 2. Problem

当前仓库已经存在 `create-spec-from-issue` 和 `create-implementation-from-issue` 两条 lifecycle workflow，并且实现流程会优先读取带 `plan-approved` 的 spec PR head branch。但是 issue 生命周期中还有几个容易混淆的点：

- 维护者不清楚 `plan-approved`、`ready-to-spec`、`ready-to-implement` 分别应该贴在哪里。
- spec PR 获批后，issue 上的 `ready-to-spec` 如果继续保留，会让 issue 长期处于已经完成 spec 但仍显示待写 spec 的状态。
- `plan-approved` 是否应该自动添加 `ready-to-implement` 缺少明确边界，容易误触发实现。
- 当 issue 同时带有 `ready-to-spec` 和 `ready-to-implement` 时，需要保证 implementation 优先，避免两个 workflow 竞争或重复工作。
- 用户会质疑为什么实现不必等 spec PR merge 到主干后才开始，需要把“内容审批”和“Git 历史落地”的语义分开。

## 3. Goals

- 在 linked spec PR 添加 `plan-approved` 时，自动从 linked issue 移除 `ready-to-spec`。
- 不因 `plan-approved` 自动添加 `ready-to-implement`。
- 当 linked issue 已经有 `ready-to-implement` 且 bot 已分配时，允许 approval 后自动触发 implementation workflow。
- 当 linked issue 没有 `ready-to-implement` 或 bot 未分配时，只同步 issue 状态，不启动实现。
- 让 `ready-to-implement` 在 issue 同时带两个生命周期 label 的短暂状态中优先于 `ready-to-spec`。
- 保持 approved open spec PR 可作为 implementation 的 authoritative spec context，不要求 spec PR 先 merge 到主干。
- 明确推荐的人工协作顺序，降低维护者误操作概率。

## 4. Non-goals

- 不改变 `ready-to-spec` 触发 spec PR 创建的核心语义。
- 不改变 `ready-to-implement` 触发 implementation workflow 的核心语义。
- 不自动 merge spec PR。
- 不要求 implementation 必须等待 spec PR merge 到 default branch。
- 不自动给 issue 添加 `ready-to-implement`。
- 不长期支持 issue 同时保留 `ready-to-spec` 和 `ready-to-implement` 作为推荐状态；只要求短暂并发状态安全。
- 不改变 branch protection、PR review 或人工审批权限规则。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub Actions lifecycle 行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### Label 语义

| label | 通常贴哪 | 表示什么 | 主要用途 |
| --- | --- | --- | --- |
| `plan-approved` | spec PR | spec / plan 已批准 | 让 workflow 把该 spec PR 内容作为 authoritative spec context |
| `ready-to-spec` | issue | issue 需要先写 spec | 触发或允许 `create-spec-from-issue` |
| `ready-to-implement` | issue | issue 可以实现了 | 触发或允许 `create-implementation-from-issue` |

### 推荐流程

1. 维护者给 issue 添加 `ready-to-spec`，并确保 bot 已分配。
2. `create-spec-from-issue` 创建 spec PR。
3. 维护者 review spec PR。
4. 维护者在 spec PR 上添加 `plan-approved`。
5. workflow 自动从 linked issue 移除 `ready-to-spec`。
6. 维护者给 issue 添加 `ready-to-implement`，并确保 bot 已分配。
7. `create-implementation-from-issue` 基于 approved spec PR 的 head branch 启动实现。

更稳妥的人工顺序是先 approve spec PR，再推进 issue：先给 spec PR 添加 `plan-approved`，再给 issue 添加 `ready-to-implement` 或确认 bot assignment。

### `plan-approved` 行为

- 当 `plan-approved` 添加到 spec PR 时，系统必须尝试解析 linked issue。
- 如果 linked issue 存在且带有 `ready-to-spec`，系统必须移除该 label。
- 如果 linked issue 不带 `ready-to-spec`，系统应保持幂等，不报错、不重新添加 label。
- `plan-approved` 不应自动给 linked issue 添加 `ready-to-implement`。
- `plan-approved` 表示 spec 内容可以作为实现依据，不表示 spec PR 已经 merge。
- 如果 spec PR 被误打 `plan-approved`，后续实现可能基于错误 plan；维护者应移除或更正 label 后重新推进。

### Implementation 触发行为

- implementation 的自动启动条件必须是：linked issue 已有 `ready-to-implement`，且 bot 已分配。
- 如果 `plan-approved` 发生时 linked issue 已经满足 implementation 条件，系统可以自动触发 `create-implementation-from-issue`。
- 如果 linked issue 没有 `ready-to-implement`，系统只移除 `ready-to-spec` 并结束，不启动实现。
- 如果 linked issue 有 `ready-to-implement` 但 bot 未分配，系统只同步状态，不启动实现。
- 如果 issue 同时带有 `ready-to-spec` 和 `ready-to-implement`，implementation 优先；spec workflow 不应再创建新的 spec PR。

### 同时存在两个 lifecycle label 的场景

| 场景 | 预期结果 |
| --- | --- |
| issue 已有两个 label，然后 `@bot` | 只跑 implementation，`ready-to-implement` 优先 |
| issue 已有两个 label，然后 assign bot | 只跑 implementation，`ready-to-implement` 优先 |
| 先给已分配 bot 的 issue 加 `ready-to-spec` | 触发 `create-spec-from-issue` |
| 再给同一个 issue 加 `ready-to-implement` | 触发 `create-implementation-from-issue` |
| spec PR 加 `plan-approved`，issue 同时有 `ready-to-implement` + bot | 移除 `ready-to-spec` 并触发 implementation |

系统应允许短暂的 mid-promotion 状态，但不应把两个 label 长期共存作为推荐用法。

### 为什么不要求 spec 先 merge 到主干

`plan-approved` 和 merge 的语义应保持分离：

- `plan-approved` = 内容审批通过，可以作为 implementation 的 authoritative context。
- merge = spec 文档进入 Git 历史主干。

实现流程应优先读取 approved spec PR 的 head branch 上的：

- `specs/issue-<issue_number>/product.md`
- `specs/issue-<issue_number>/tech.md`

这样可以减少串行等待，避免实现读到 default branch 上的旧 spec，并允许 spec PR 仍在等待 CI、branch protection 或管理员操作时先解锁实现。

## 7. Success criteria

- 当 spec PR 被添加 `plan-approved` 且能解析到 linked issue 时，linked issue 上的 `ready-to-spec` 会被自动移除。
- `plan-approved` 不会自动添加 `ready-to-implement`。
- 当 linked issue 已经有 `ready-to-implement` 且 bot 已分配时，`plan-approved` 后 implementation workflow 会被触发或等价地进入可执行状态。
- 当 linked issue 缺少 `ready-to-implement` 或 bot assignment 时，`plan-approved` 只同步状态，不启动实现。
- issue 同时带 `ready-to-spec` 和 `ready-to-implement` 时，spec workflow 不会运行，implementation workflow 优先。
- implementation workflow 继续优先使用 labeled `plan-approved` spec PR 的 head branch 作为 spec context。
- 重复添加或处理 `plan-approved` 不会导致重复 label 操作失败、重复 spec PR 创建或不必要的 implementation PR。
- 无法解析 linked issue、linked issue 已关闭、label 不存在或权限不足等异常场景有清晰日志，且不会误触发实现。

## 8. Validation

- 用自动化测试覆盖 `plan-approved` PR label 事件解析 linked issue、移除 `ready-to-spec`、不添加 `ready-to-implement`。
- 用自动化测试覆盖 issue 同时有两个 lifecycle label 时 implementation 优先、spec workflow 跳过。
- 用自动化测试覆盖 `ready-to-implement` + bot assignment 存在时，approval 后会触发或调度 implementation。
- 用自动化测试覆盖缺少 `ready-to-implement`、缺少 bot assignment、找不到 linked issue、重复处理等幂等分支。
- 人工检查 GitHub Actions workflow，确认所需 permissions 足够移除 issue label 并触发 implementation。
- 人工验证一次完整 happy path：`ready-to-spec` issue → spec PR → `plan-approved` → issue 移除 `ready-to-spec` → maintainer 添加 `ready-to-implement` → implementation 使用 approved spec PR context。

## 9. Open questions

- linked issue 的解析是否只依赖 PR body 中的 `Refs #<number>` / closing keyword，还是也需要支持 branch name `spec/issue-<number>` 作为 fallback？本规格建议支持 PR body 优先、branch name fallback。
- 如果 `ready-to-implement` 已存在但 bot 未分配，是否需要自动分配 bot？本规格按 issue 描述保持保守：不自动分配，只同步状态。
- 如果 spec PR 上移除 `plan-approved`，是否需要回滚 issue label 状态？本规格不要求回滚。
