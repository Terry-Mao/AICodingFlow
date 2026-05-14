# 产品规格：plan-approved 同步 issue 生命周期状态

## 1. Summary

本功能完善 spec-first GitHub Actions 生命周期：当维护者在 spec PR 上添加 `plan-approved` 后，系统应自动把 linked issue 从“需要写 spec”的状态推进出来，移除 issue 上的 `ready-to-spec`。如果 linked issue 已经同时满足实现启动条件，即带有 `ready-to-implement` 且已分配给配置的 bot，则系统应在完成状态同步后自动触发 `create-implementation-from-issue`。

期望结果是：`plan-approved` 表示 spec PR 内容已被批准并可作为 authoritative spec context；`ready-to-implement` 仍然是进入实现阶段的显式 issue label；两个 label 的职责清晰，workflow 执行顺序稳定，不会因为短暂的 mid-promotion 状态重复或反向触发错误阶段。

## 2. Problem

当前 issue 流程已经区分 `ready-to-spec`、`plan-approved` 和 `ready-to-implement`，但 `plan-approved` 后的状态同步和实现触发规则不够完整。维护者批准 spec PR 后，如果系统不自动移除 linked issue 上的 `ready-to-spec`，issue 会长期保留过期生命周期 label，后续 agent 或维护者难以判断它仍需补 spec，还是已经等待实现。

同时，spec PR 被批准后不要求先 merge 到主干；实现流程会优先读取 labeled `plan-approved` 的 spec PR head branch。因此系统需要把“内容批准”和“merge 落地”分开处理：`plan-approved` 解锁实现上下文，merge 只是 Git 历史落地。

## 3. Goals

- 当 spec PR 被添加 `plan-approved` label 时，自动定位 linked issue。
- 自动移除 linked issue 上的 `ready-to-spec`。
- 不自动添加 `ready-to-implement`；该 label 仍由维护者或外部流程显式添加。
- 如果 linked issue 已有 `ready-to-implement` 且 assignee 包含配置的 bot，则在移除 `ready-to-spec` 后自动触发 `create-implementation-from-issue`。
- 如果 linked issue 没有 `ready-to-implement`，或者 bot 未分配，只同步状态，不启动实现。
- 当 issue 同时短暂存在 `ready-to-spec` 和 `ready-to-implement` 时，`ready-to-implement` 优先，避免 spec workflow 抢跑。
- 允许 spec PR 未 merge 时被实现流程作为 authoritative spec context 使用，只要它带有 `plan-approved`。
- 保持人工协作流程清晰：维护者批准 spec PR，再决定何时推进 issue 到实现阶段。

## 4. Non-goals

- 不改变 `plan-approved` 的含义为 merge gate；它只表示内容审批通过。
- 不要求 spec PR 必须先 merge 到 `main` 才能实现。
- 不在 `plan-approved` 时自动添加 `ready-to-implement`。
- 不改变 implementation PR 的创建、提交、push 或 PR body 规则。
- 不改变 spec 文件生成流程的输出契约。
- 不长期支持 issue 同时保留多个生命周期 label 作为理想状态；只要求短暂 mid-promotion 状态行为稳定。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub Actions lifecycle 和 label 状态同步变更，不涉及 UI 或视觉设计。

## 6. User experience

### 生命周期 label 语义

| label | 通常贴哪 | 表示什么 | 主要用途 |
| --- | --- | --- | --- |
| `ready-to-spec` | issue | issue 需要先写 spec | 触发或允许 `create-spec-from-issue` |
| `plan-approved` | spec PR | spec/plan 已批准 | 让 workflow 把该 spec PR 内容作为 authoritative spec context |
| `ready-to-implement` | issue | issue 可以实现了 | 触发或允许 `create-implementation-from-issue` |

### 标准协作流程

1. 维护者给 issue 添加 `ready-to-spec` 并分配 bot。
2. `create-spec-from-issue` 创建 spec PR。
3. 维护者 review spec PR。
4. 维护者给 spec PR 添加 `plan-approved`。
5. workflow 找到 linked issue，并自动移除 issue 上的 `ready-to-spec`。
6. 维护者在 issue 上添加 `ready-to-implement` 并确保 bot 已分配，或者在添加 `plan-approved` 前 issue 已经具备这两个条件。
7. 当 issue 同时具备 `ready-to-implement` 和 bot assignee 时，实现 workflow 可以启动。

### `plan-approved` 后的行为规则

- 当 `plan-approved` 添加到非 PR issue 上时，不应执行 spec approval 状态推进。
- 当 `plan-approved` 添加到 PR，但无法解析 linked issue 时，应停止并输出清晰原因，不应修改任何 issue label。
- 当 linked issue 带有 `ready-to-spec` 时，workflow 必须移除它。
- 当 linked issue 没有 `ready-to-spec` 时，workflow 应视为幂等成功，不应失败。
- workflow 不得因为 `plan-approved` 自动给 issue 添加 `ready-to-implement`。
- 当 linked issue 已有 `ready-to-implement` 且 assignee 包含 bot 时，workflow 在移除 `ready-to-spec` 后触发 `create-implementation-from-issue`。
- 当 linked issue 缺少 `ready-to-implement` 时，workflow 只同步状态，不启动实现。
- 当 linked issue 有 `ready-to-implement` 但没有 bot assignee 时，workflow 只同步状态，不启动实现。
- 当 issue 同时有 `ready-to-spec` 和 `ready-to-implement` 时，implementation 优先；spec workflow 不应因为 `ready-to-spec` 再生成或更新 spec PR。

### 触发场景矩阵

| 场景 | 期望结果 |
| --- | --- |
| issue 已有 `ready-to-spec` 和 `ready-to-implement`，然后 `@bot` | 只跑 implementation，`ready-to-implement` 优先 |
| issue 已有 `ready-to-spec` 和 `ready-to-implement`，然后 assign bot | 只跑 implementation，`ready-to-implement` 优先 |
| 先给已分配 bot 的 issue 加 `ready-to-spec` | 触发 `create-spec-from-issue` |
| 再给同一个 issue 加 `ready-to-implement` | 触发 `create-implementation-from-issue`，前提是实现上下文满足要求 |
| spec PR 加 `plan-approved`，issue 同时有 `ready-to-implement` 和 bot | 移除 `ready-to-spec`，然后触发 implementation |
| spec PR 加 `plan-approved`，issue 没有 `ready-to-implement` | 只移除 `ready-to-spec`，不启动 implementation |
| spec PR 加 `plan-approved`，issue 没有 bot assignee | 只移除 `ready-to-spec`，不启动 implementation |

### authoritative spec context

- `plan-approved` 的 spec PR 可以在未 merge 时作为 authoritative spec context。
- implementation workflow 应优先读取 linked issue 对应的 `spec/issue-<issue_number>` open PR 中最新带 `plan-approved` 的 head branch。
- 如果没有 approved spec PR，implementation workflow 才回退到仓库中已存在的 `specs/issue-<issue_number>/product.md` 和 `specs/issue-<issue_number>/tech.md`。
- 维护者误打 `plan-approved` 会让实现基于错误 plan，因此该 label 应被视为内容审批动作。

## 7. Success criteria

- 在 spec PR 上添加 `plan-approved` 后，linked issue 上的 `ready-to-spec` 会被自动移除。
- `plan-approved` 不会自动添加 `ready-to-implement`。
- linked issue 没有 `ready-to-spec` 时，approval workflow 可以幂等完成。
- linked issue 没有 `ready-to-implement` 时，不会启动 implementation。
- linked issue 有 `ready-to-implement` 但没有 bot assignee 时，不会启动 implementation。
- linked issue 同时有 `ready-to-implement` 和 bot assignee 时，approval workflow 在状态同步后触发 `create-implementation-from-issue`。
- 当 issue 同时有 `ready-to-spec` 和 `ready-to-implement` 时，spec generation workflow 不运行，implementation workflow 优先。
- implementation workflow 能继续使用带 `plan-approved` 的 open spec PR head branch 作为 authoritative spec context。
- workflow 日志或输出能说明未触发 implementation 的具体原因，例如缺少 `ready-to-implement`、缺少 bot assignee 或无法解析 linked issue。

## 8. Validation

- 用单元测试覆盖 linked issue 解析、label 移除、幂等无 label、缺少 linked issue、缺少 bot assignee 和缺少 `ready-to-implement` 的分支。
- 用 workflow 或脚本级测试覆盖 `plan-approved` 事件触发后先移除 `ready-to-spec`、再按条件触发 implementation。
- 用测试或静态检查确认 `create-spec-from-issue` 在 issue 同时带有 `ready-to-implement` 时跳过。
- 手工验证一个 spec PR 未 merge 但带 `plan-approved` 时，implementation context 仍优先读取该 PR head branch 上的 specs。
- 手工验证 `plan-approved` 不会自动添加 `ready-to-implement`。

## 9. Open questions

- linked issue 的解析是否只依赖 PR body 中的 `Refs #57` 等引用，还是也应支持 branch name `spec/issue-57` 作为 fallback？本规格建议两者都支持，优先使用明确的 PR body reference。
- 自动触发 implementation 应使用 `workflow_dispatch` 调用 `create-implementation-from-issue.yml`，还是通过 issue label/assignment 事件自然触发？本规格建议用显式 workflow dispatch，避免为了触发 workflow 而重复编辑 issue。
