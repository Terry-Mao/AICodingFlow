# 技术规格：`plan-approved` lifecycle 同步与 workflow 顺序优化

## 1. Problem

当前仓库已有 spec 创建和 implementation 创建 workflow，但缺少一个明确处理 `plan-approved` PR label 的 lifecycle 同步入口。`write_spec_context.py` 和 `prepare_issue_implementation_context.py` 已经把 `plan-approved` 作为选择 approved spec PR 的信号；`create-spec-from-issue.yml` 也已经在 job 级别排除带 `ready-to-implement` 的 issue。因此本次实现重点不是重写现有 workflow，而是补齐 `plan-approved` 事件后的 issue 状态同步和 implementation 调度顺序。

技术目标是新增或调整 workflow / helper script，使 `plan-approved` 添加到 spec PR 后可以安全地：

1. 找到 linked issue。
2. 移除 linked issue 上的 `ready-to-spec`。
3. 在 linked issue 已经满足 `ready-to-implement` + bot assignment 时触发 implementation。
4. 保持幂等，并避免 spec workflow 与 implementation workflow 同时误跑。

## 2. Relevant code

- `.github/workflows/create-spec-from-issue.yml` — 监听 issue `labeled`、`assigned`、`issue_comment`；当前 job 条件要求 issue 有 `ready-to-spec` 且没有 `ready-to-implement`。
- `.github/scripts/prepare_issue_spec_context.py` — spec workflow 的稳定上下文准备脚本；`should_run` 已在 `ready-to-implement` 存在时返回 `issue is already ready-to-implement`。
- `.github/workflows/create-implementation-from-issue.yml` — 监听 issue `labeled`、`assigned`、`issue_comment` 和 `workflow_dispatch`；当前 job 条件要求 issue 有 `ready-to-implement`。
- `.github/scripts/prepare_issue_implementation_context.py` — implementation workflow 的稳定上下文准备脚本；会查找 linked approved spec PR，没有 approved context 但存在 linked spec PR 时进入 noop blocked 状态。
- `.github/scripts/write_spec_context.py` — PR review / implementation 共用的 approved spec context 解析逻辑；`APPROVED_LABEL = "plan-approved"`，并通过 `spec/issue-<number>` branch 查找 open spec PR。
- `.github/scripts/validate_spec_output.py` — spec 生成输出校验脚本，确认本次 spec-only 产物范围。
- `.github/scripts/finalize_implementation_pr.py` — implementation PR 创建 / 更新逻辑；当 implementation 来自 approved spec PR 时，会更新 selected spec PR。

## 3. Current state

当前状态：

- `create-spec-from-issue.yml` 不会在 issue 已有 `ready-to-implement` 时运行，这已经体现了 implementation 优先的基本策略。
- `prepare_issue_spec_context.py` 在 `ready-to-implement` 存在时也会跳过 spec 创建。
- `create-implementation-from-issue.yml` 只由 issue 事件、issue comment 或手动 dispatch 触发，不会直接响应 spec PR 上的 `plan-approved` label。
- `prepare_issue_implementation_context.py` 会优先选择带 `plan-approved` 的 linked spec PR，并从该 PR head branch 读取 spec 文件。
- `write_spec_context.py` 已有 `APPROVED_LABEL` 和 spec PR 查找逻辑，但没有负责修改 issue label。
- 仓库中没有专门响应 `pull_request` / `pull_request_target` `labeled` 事件并处理 `plan-approved` 的 workflow。

限制：

- spec PR 获批后，issue 上的 `ready-to-spec` 不会被自动移除。
- 如果维护者希望 approval 后立即实现，需要再通过 issue label / assignment / comment / manual dispatch 触发 implementation。
- 缺少统一脚本封装 linked issue 解析、label 移除、implementation 是否应触发的判断，测试边界不集中。

## 4. Proposed changes

### 新增 `plan-approved` 同步入口

新增一个 GitHub Actions workflow，建议命名为 `.github/workflows/plan-approved.yml` 或类似名称，监听 spec PR label 事件：

```yaml
on:
  pull_request_target:
    types: [labeled]
```

job 条件应要求：

- `github.event.label.name == 'plan-approved'`
- PR 来自本仓库分支，或后续脚本能安全处理 head branch。
- PR 能解析出 issue number。

使用 `pull_request_target` 的原因是该 workflow 需要写 issue label、可能触发另一个 workflow，并且不需要执行 PR head 中的代码。实现时不得 checkout 或执行不受信任 head branch 脚本；只运行 default branch 中的 repository scripts。

如果维护者更倾向避免 `pull_request_target`，也可以使用 `pull_request` + `permissions: issues: write, actions: write`，但 fork PR 场景权限可能不足。本仓库 spec PR 通常由 bot 在同仓库分支创建，二者都可行；推荐选择权限语义更明确且不执行 head code 的 `pull_request_target`。

### 新增 helper script

新增脚本，建议路径为 `.github/scripts/handle_plan_approved.py`。职责：

- 读取 GitHub event payload。
- 验证当前事件是 PR 上添加 `plan-approved`。
- 解析 linked issue number。
- 读取 issue 当前 labels 和 assignees。
- 如果 issue 有 `ready-to-spec`，调用 GitHub API 移除该 label。
- 判断 issue 是否同时具备 `ready-to-implement` 和 configured bot assignee。
- 输出结构化 GitHub outputs，供 workflow 决定是否 dispatch implementation。

建议输出字段：

- `should_run`: 当前事件是否需要处理。
- `issue_number`: linked issue number。
- `removed_ready_to_spec`: 是否实际移除了 `ready-to-spec`。
- `should_dispatch_implementation`: 是否应触发 implementation。
- `skip_reason`: 跳过原因。
- `dispatch_reason`: 触发 implementation 的原因。

### linked issue 解析

复用或提取 `write_spec_context.py` 中的 issue number 解析思路，保持与 review / implementation context 逻辑一致：

1. 优先从 PR body 解析 `Refs #<number>`、`Closes #<number>`、`Fixes #<number>`、`issue #<number>` 等文本。
2. 如果 PR body 无法解析，从 PR title 解析。
3. 如果仍无法解析，从 head branch `spec/issue-<number>` 解析。

解析失败时 workflow 应跳过并记录原因，不应修改任何 issue。

### label 移除

脚本应使用 GitHub API 或 `gh issue edit --remove-label ready-to-spec` 移除 label。推荐直接使用 GitHub API / `gh api`，便于区分 404、label 不存在和权限错误。

行为要求：

- issue 没有 `ready-to-spec` 时视为成功的幂等状态。
- issue 已关闭时默认仍可移除 label，但不应触发 implementation；如果 GitHub 权限或仓库策略阻止修改，应记录失败并让 workflow fail 或明确 blocked。建议 fail fast，因为 label 同步是该 workflow 的核心职责。
- 不添加 `ready-to-implement`。
- 不移除 `ready-to-implement`。

### implementation 调度

当 helper script 输出 `should_dispatch_implementation=true` 时，workflow 应触发 `create-implementation-from-issue.yml`：

```bash
gh workflow run create-implementation-from-issue.yml \
  --ref "$DEFAULT_BRANCH" \
  -f issue="$ISSUE_NUMBER" \
  -f agent_login="$AGENT_LOGIN"
```

前置条件：

- linked issue labels 包含 `ready-to-implement`。
- linked issue assignees 包含 `AGENT_LOGIN`。
- 当前 PR 已添加 `plan-approved`。

这样可以复用 `create-implementation-from-issue.yml` 和 `prepare_issue_implementation_context.py` 的既有 approved spec PR 选择逻辑，避免把 implementation branch、spec context 或 PR 更新逻辑复制到新 workflow。

### workflow permissions

建议 workflow permissions：

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: read
  actions: write
```

- `issues: write` 用于移除 issue label。
- `pull-requests: read` 用于读取 PR context。
- `actions: write` 用于 `gh workflow run`。
- `contents: read` 用于 checkout default branch 中的 scripts。

如果实现选择直接调用 repository dispatch 或 issues event 而非 `gh workflow run`，可相应调整权限，但必须在 tech spec 更新中说明。

### 保持现有 workflow 优先级

保留 `create-spec-from-issue.yml` 的 job 条件：

- issue 必须有 `ready-to-spec`。
- issue 不能有 `ready-to-implement`。

保留 `prepare_issue_spec_context.py` 的 `ready-to-implement` guard，作为 workflow 条件之外的二次防线。

保留 `create-implementation-from-issue.yml` 的 issue-level trigger 条件。新增 `workflow_dispatch` 调度只是让 `plan-approved` 事件可以在条件满足时显式复用该 workflow。

### 避免重复触发

需要考虑以下幂等策略：

- GitHub `labeled` 事件只在 label 新增时触发；重复处理同一事件一般不会发生。
- 如果 workflow rerun，移除 `ready-to-spec` 时应看到 label 已不存在并继续。
- 如果 implementation 已有 open PR，`prepare_issue_implementation_context.py` / downstream scripts 已有现有 PR 检查或更新逻辑；新 workflow 不应重复实现该判断。
- 如果 issue 有 `ready-to-implement` 但没有 approved spec context，`prepare_issue_implementation_context.py` 会发现当前 `plan-approved` PR 并读取其 head branch；如果读取失败，会按现有 noop / blocked 逻辑处理。

## 5. End-to-end flow

### spec-only path

1. Issue 带 `ready-to-spec` 且 bot 已分配。
2. `create-spec-from-issue.yml` 创建或更新 `spec/issue-<number>` PR。
3. 维护者 review spec PR。
4. 维护者在 spec PR 添加 `plan-approved`。
5. 新 workflow 解析 linked issue。
6. 新 workflow 从 issue 移除 `ready-to-spec`。
7. 如果 issue 没有 `ready-to-implement`，workflow 结束。

### approval 后立即 implementation path

1. Issue 已经带 `ready-to-spec`、`ready-to-implement`，且 bot 已分配，或维护者在 approval 前已经加好 `ready-to-implement`。
2. 维护者在 spec PR 添加 `plan-approved`。
3. 新 workflow 移除 issue 上的 `ready-to-spec`。
4. 新 workflow dispatch `create-implementation-from-issue.yml`。
5. implementation workflow 的 context script 找到带 `plan-approved` 的 linked spec PR。
6. implementation 从 spec PR head branch 读取 `product.md` / `tech.md` 并继续既有实现流程。

### mid-promotion issue event path

1. Issue 同时短暂拥有 `ready-to-spec` 和 `ready-to-implement`。
2. 如果发生 issue assignment、mention 或 `ready-to-implement` label event，`create-implementation-from-issue.yml` 可以运行。
3. `create-spec-from-issue.yml` 的 job 条件和 `prepare_issue_spec_context.py` 的 guard 会阻止 spec workflow 再运行。

## 6. Risks and mitigations

- 风险：`pull_request_target` 被误用执行 PR head 代码。
  - 缓解：workflow 只 checkout default branch，只运行仓库默认分支中的 scripts，不执行 head branch 文件或安装来自 PR 的依赖。
- 风险：linked issue 解析错误导致移除错误 issue 的 label。
  - 缓解：优先使用 PR body 的明确 issue reference；branch fallback 只接受严格的 `spec/issue-<number>`。
- 风险：`plan-approved` 被误加后触发实现。
  - 缓解：实现仍要求 issue 已有 `ready-to-implement` 且 bot 已分配；`plan-approved` 本身不添加 `ready-to-implement`。
- 风险：移除 `ready-to-spec` 成功但 dispatch implementation 失败。
  - 缓解：workflow 应让 dispatch step 失败并暴露日志；issue 状态仍符合“spec 已 approved，不再 ready-to-spec”。
- 风险：workflow dispatch 权限不足。
  - 缓解：显式设置 `actions: write`，并在测试 / dry run 中验证 `gh workflow run`。
- 风险：两个 workflow 同时由不同事件触发 implementation。
  - 缓解：`create-implementation-from-issue.yml` 已有 concurrency group `create-implementation-from-issue-${issue}`，并且 downstream PR 更新逻辑应保持幂等。

## 7. Testing and validation

新增或更新测试建议：

- 为新增 helper script 添加单元测试，覆盖：
  - 从 PR body 解析 `Refs #57`。
  - 从 branch `spec/issue-57` fallback 解析 issue。
  - 无法解析 issue 时跳过。
  - issue 有 `ready-to-spec` 时调用 label 移除。
  - issue 没有 `ready-to-spec` 时幂等成功。
  - issue 有 `ready-to-implement` 且 assignees 包含 bot 时输出 `should_dispatch_implementation=true`。
  - issue 有 `ready-to-implement` 但 bot 未分配时不 dispatch。
  - issue 没有 `ready-to-implement` 时不 dispatch。
- 为 `prepare_issue_spec_context.py` 或现有测试补充双 label 场景，确认 `ready-to-implement` 优先导致 spec workflow skip。
- 如果已有 workflow lint / YAML validation，加入新 workflow 的语法检查。
- 手动 dry run：
  - 在测试 issue / PR 上添加 `plan-approved`。
  - 确认 linked issue 移除 `ready-to-spec`。
  - 不带 `ready-to-implement` 时不启动 implementation。
  - 带 `ready-to-implement` 且 bot 已分配时启动 implementation，并读取 approved spec PR context。

建议命令：

```bash
python3 -m unittest discover -s tests
```

如果实现只新增脚本测试，也可以运行更小范围的相关测试模块。

## 8. Follow-ups

- 可在 README 或维护者文档中补充 lifecycle label 表和推荐人工流程。
- 可在 `plan-approved` workflow 完成后发布 issue comment，说明是否移除了 `ready-to-spec` 以及是否触发 implementation；本规格不要求必须评论。
- 可支持移除 `plan-approved` 后的状态回滚策略；本规格不要求。
