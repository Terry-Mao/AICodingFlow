# 产品规格：`create-implementation-from-issue` 自动实现 workflow

## 1. Summary

新增一个 GitHub Actions workflow，用于把已经准备实现的 GitHub issue 交给 Codex agent 自动产出实现分支，并由外层 workflow 创建或更新 implementation PR。该 workflow 面向已经完成 triage/spec 阶段的 issue，只有在明确满足 `ready-to-implement` 和 bot assignment 等 issue 条件时才会启动实现；approved spec PR 只用于选择实现上下文。

期望结果是：普通新 issue 不会被直接实现；准备好的 issue 可以复用 approved spec PR 或仓库内 specs 作为实现上下文；agent 只负责代码、必要规格同步、验证、`implementation_summary.md` 和 `pr-metadata.json`；GitHub Actions 负责解析上下文、守卫未批准计划、提交并推送实现分支、创建或更新 PR、更新 progress comment。

## 2. Problem

当前仓库已有从 GitHub issue 创建 spec PR 的 workflow，但还缺少从已批准或已准备好的 issue 自动进入实现阶段的 workflow。没有该能力时，维护者需要手动把 issue/spec 上下文整理给 agent，并手动处理 target branch、既有 PR、progress comment 和实现 PR 创建逻辑，容易导致重复劳动和执行不一致。

该功能解决的用户问题包括：

- 维护者需要一个明确、可重复的方式把 `ready-to-implement` issue 派发给 bot。
- reviewer 需要知道实现是否基于 approved spec，而不是基于未批准的 plan 或零散评论。
- agent 需要稳定、结构化的 issue/spec 上下文，避免直接信任 issue comments 或误用错误分支。
- workflow 需要在无实现 diff、已有 draft PR、approved spec PR 和未批准 spec PR 等状态下给出一致结果。

## 3. Goals

- 新增 `create-implementation-from-issue` workflow，处理从 GitHub issue 到 implementation PR 的自动化链路。
- 支持以下触发条件：
  - issue 已有 `ready-to-implement`，且 bot 被 assign。
  - issue 已 assign 给 bot，后来新增 `ready-to-implement`。
  - `ready-to-implement` issue 下出现显式 `@bot` 评论。
- 收集稳定上下文，包括 issue 基本信息、labels、assignees、default branch、target branch、spec context 来源、selected spec PR、是否已有 implementation PR、spec context text、coauthor directives、skill paths 和 progress comment 定位信息。
- 按确定优先级解析 spec context：
  - 优先使用带 `plan-approved` 的 `spec/issue-<issue-number>` spec PR。
  - 其次使用默认分支的 `specs/issue-<issue-number>/product.md` 和 `specs/issue-<issue-number>/tech.md`。
  - 没有任何 spec context 时允许继续实现，但必须在 agent prompt 中明确说明没有 spec context。
- 当存在未批准 spec PR 且默认分支没有 specs 时，workflow 必须 noop，不启动实现，并在 progress comment 中说明原因。
- 当使用 approved spec PR 时，目标分支必须是 selected spec PR 的 head branch，让 spec 和 implementation 在同一个 PR 中继续演进。
- 当没有 approved spec PR 时，目标分支必须默认为 `spec/implement-issue-<issue_number>`，并允许 workflow 更新已有 draft implementation PR 或创建新的 draft implementation PR。
- 派发 agent 时要求读取 `implement-specs`、`spec-driven-implementation`、`implement-issue` 三类技能职责。
- agent 输出存在实现 diff 时，必须产生代码变更、必要时同步 specs、写出 `implementation_summary.md` 和 `pr-metadata.json`，并把实现 diff 留在工作区；不得自行 commit、push、创建或更新 PR。
- 外层 workflow 必须校验 `pr-metadata.json`，提交并推送实现分支，根据 branch 更新创建或更新 PR，并更新 issue progress comment。

## 4. Non-goals

- 不让普通新 issue 绕过 triage/spec 阶段直接实现。
- 不把未批准的 spec PR 当作实现依据。
- 不要求 agent 调用 GitHub API 创建、编辑或发布 PR。
- 不要求 agent 直接更新 issue progress comment；progress comment 由外层 workflow 维护。
- 不在本规格中定义具体业务功能实现方式；本规格只定义自动化 workflow 行为。
- 不替代现有 `create-spec-from-issue` workflow。
- 不要求 implementation PR 一定从 spec PR 分离；当 spec PR 已批准时，implementation 应直接追加到该 PR 的 branch。

## 5. Figma / design references

Figma: none provided。该需求是 GitHub workflow、agent skill 和自动化行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### 默认触发与守卫

- 如果 issue 没有 `ready-to-implement`，workflow 不启动实现。
- 手动触发也必须满足 `ready-to-implement` 和 bot assignment，不作为跳过 triage/spec 的 override。
- 如果 issue 没有 assign 给配置的 bot，且触发评论没有显式 mention bot，workflow 不启动实现。
- Spec PR 的 `plan-approved` label 只用于选择 approved spec context，不作为 implementation workflow 的触发源。
- workflow 会 best-effort 把 bot 加回 issue assignee；失败不应阻止后续实现，除非后续权限或上下文缺失导致无法继续。
- workflow 必须把 issue body 和 comments 当作不可信数据，只提取上下文，不允许其中内容覆盖系统规则、skill 规则、输出路径或安全边界。

### spec context 行为

- 若找到 approved spec PR：
  - `spec_context_source = approved-pr`。
  - 选择最新或最合适的 approved spec PR。
  - 从该 PR head branch 读取 `specs/issue-<issue-number>/product.md` 与 `tech.md`。
  - `target_branch = selected_spec_pr.head_ref_name`。
  - 后续实现追加到该 spec PR 分支。
- 若没有 approved spec PR，但默认分支存在 specs：
  - `spec_context_source = directory`。
  - 从默认分支读取 specs。
  - `target_branch = spec/implement-issue-<issue_number>`。
  - 后续创建或更新 draft implementation PR。
- 若没有任何 spec context：
  - workflow 仍可启动实现。
  - agent prompt 必须明确说明没有 approved 或 repository spec context。
  - 后续创建或更新 draft implementation PR。
- 若存在 unapproved spec PR，且默认分支没有 specs：
  - `should_noop = true`。
  - workflow 不启动 agent。
  - progress comment 说明：`linked spec PR(s) exist ... but none are labeled plan-approved`。

### agent 执行行为

- workflow 必须在运行 agent 前 checkout target branch；若 branch 已存在则 fetch 并继续，否则从 default branch 创建。
- agent 必须按 `spec_context_text` 对齐实现；若 implementation 与 specs 有意偏离，必须在同一变更中更新 `product.md` 或 `tech.md`。
- agent 可以按需读取 issue body/comments，但必须把 fetched issue content 当作数据而不是指令。
- agent 必须运行相关验证，并在最终说明中报告验证结果。
- 如果没有产生实现 diff，agent 不应制造空提交。
- 如果产生实现 diff，agent 必须写出 `implementation_summary.md` 和 `pr-metadata.json`，包含：
  - `branch_name`：外层 workflow 应提交并推送的分支。没有 approved spec PR 时，可以在默认 target branch 后追加简短 slug。
  - `pr_title`：conventional commit style，基于实际代码变更。
  - `pr_summary`：完整 PR body，第一行必须是 `Closes #<issue_number>`。
  - `intended_files`：外层 workflow 应提交的 repository-relative 实现文件列表，不包含 workflow 临时文件、validation logs、生成缓存或未变化文件。
- agent 停止于工作区 diff 和 metadata handoff；不得自行 commit、push、open/update PR。

### 外层 workflow 结果行为

- 如果 `should_noop`，只更新 progress comment，不创建 PR。
- agent 运行后，workflow 必须检查是否存在非临时实现 diff。
- workflow 必须读取 `pr-metadata.json`；若 metadata 缺失或无效，应在 progress comment 中说明失败状态。
- metadata 校验通过后，workflow 必须提交并推送 `branch_name`，再检查该 branch 是否在 run 开始后更新过。
- 若 agent 在允许范围内扩展了 branch name，workflow 使用 metadata 中的 branch 更新后续 PR 操作。
- 如果 branch 没有更新，progress comment 写：`I analyzed this issue but did not produce an implementation diff.`。
- 如果有 approved spec PR，workflow 更新原 spec PR 的 title/body，使它成为 spec + implementation PR。
- 如果没有 approved spec PR，workflow 查找 `head=owner:target_branch` 的 open PR：
  - 已存在则更新 title/body。
  - 不存在则创建新的 draft PR。
- workflow 完成后，progress comment 应告诉用户创建或更新了哪个 PR，并包含下一步：
  - `Review the implementation changes in the PR.`
  - `Complete any manual verification needed before merging.`

## 7. Success criteria

- `ready-to-implement` + bot assigned 的 issue 会启动实现上下文准备。
- bot assigned issue 后续新增 `ready-to-implement` label 时会启动实现。
- `ready-to-implement` issue 下显式 mention bot 的评论会启动实现；引用块或部分用户名匹配不会误触发。
- spec PR 新增 `plan-approved` 不会单独启动实现；实现只由 issue 本身的 ready/assignment/mention 状态触发。
- approved spec PR 优先于默认分支 specs，并使 implementation 推送到 approved spec PR 的 head branch。
- 默认分支 specs 在没有 approved spec PR 时作为 fallback context。
- 未批准 spec PR 且无默认分支 specs 时不会启动实现，并给出明确 progress comment。
- 无 spec context 时 workflow 可以继续，但 agent prompt 必须明确告知无 spec context。
- agent prompt 明确要求读取 `implement-specs`、`spec-driven-implementation`、`implement-issue`，并区分三者职责。
- 有实现 diff 时，workflow 最终创建或更新正确 PR；无 diff 时不会创建空 PR。
- `pr-metadata.json` 的 `branch_name`、`pr_title`、`pr_summary` 被验证后才用于 PR 操作。
- approved spec PR 场景不会创建新的 draft implementation PR，而是更新原 spec PR。
- 非 approved spec PR 场景创建的新 implementation PR 必须是 draft。
- coauthor directives 只从 issue/comments 中的有效 `Co-authored-by:` 行收集，不凭空编造。

## 8. Validation

- 使用单元测试覆盖 trigger 判断、bot mention 边界、label/assignment 组合，并确认 spec PR `plan-approved` 不作为触发源。
- 使用单元测试覆盖 spec context 优先级：approved PR、默认分支 directory、none、unapproved PR noop。
- 使用单元测试覆盖 target branch 选择和允许的 branch slug 扩展。
- 使用单元测试覆盖 `pr-metadata.json` schema、conventional title、`Closes #<issue_number>` 第一行和 branch name 校验。
- 使用单元测试或脚本测试覆盖 progress comment 文案在 noop、无 diff、PR 创建、PR 更新四类结果下稳定。
- 通过 workflow 文件静态检查确认 agent prompt 使用稳定本地 context 文件，不直接把 live GitHub 内容作为指令。
- 对 happy path 进行一次手动或 dry-run 验证：从 ready issue 到 target branch 更新，再到 PR 创建或更新。

## 9. Open questions

- 默认 implementation branch 是否必须严格为 `spec/implement-issue-<issue_number>`，还是允许 workflow 一开始就追加 issue title slug？issue 当前允许 agent 在无 approved spec PR 时扩展 branch name。
- progress comment 的唯一标识和更新策略是否复用现有 comment marker，还是新增 implementation-specific marker？
- `has_existing_implementation_pr` 的定义是否只匹配 bot 创建的 draft PR，还是所有 open PR with matching head branch 都算。
