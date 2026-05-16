# 技术规格：plan-approved 状态同步与 workflow 顺序优化

## 1. Problem

issue 57 要求把 spec-first 生命周期中的 `plan-approved` 批准动作接到 issue 状态同步和实现启动流程上。当前代码中已经有 `create-spec-from-issue` 和 `create-implementation-from-issue` 两条 workflow，implementation context 也能读取带 `plan-approved` 的 spec PR，但缺少一个在 spec PR 被批准时自动移除 linked issue 上 `ready-to-spec`、并按条件触发 implementation 的入口。

技术目标是在不改变现有 spec/implementation 输出契约的前提下，新增或调整 workflow 编排，让 label 生命周期符合产品规格：`plan-approved` 只代表 spec 内容审批通过，`ready-to-implement` 仍是实现阶段的显式触发 label。

## 2. Relevant code

- `.github/workflows/create-spec-from-issue.yml` — spec generation workflow。当前触发 `ready-to-spec` label、assignment 和 issue comment，并在 job-level `if` 中排除已有 `ready-to-implement` 的 issue。
- `.github/scripts/prepare_issue_spec_context.py` — spec generation context 脚本。`should_run()` 当前在 labels 中发现 `ready-to-implement` 时返回跳过，并要求 issue 包含 `ready-to-spec`。
- `.github/workflows/create-implementation-from-issue.yml` — implementation workflow。当前触发 `ready-to-implement` label、assignment、issue comment 和 `workflow_dispatch`，并调用 `prepare_issue_implementation_context.py`。
- `.github/scripts/prepare_issue_implementation_context.py` — implementation context 脚本。当前要求 issue 包含 `ready-to-implement`，并通过 `resolve_implementation_spec_context()` 优先选择 linked issue 的 approved spec PR。
- `.github/scripts/write_spec_context.py` — spec context resolution helper。定义 `APPROVED_LABEL = "plan-approved"`，通过 `fetch_spec_prs()` 查找 `spec/issue-<issue_number>` open PR，并优先读取带 `plan-approved` 的 PR head branch。
- `.github/scripts/update_implementation_progress.py` — implementation workflow 用于向 issue 写进度 comment；approval workflow 可参考其 GitHub API 调用风格，但不应复用为 label 同步入口。
- `.github/scripts/validate_spec_output.py` — spec-only workflow 的输出校验。该 issue 的 specs 不应改变它的契约。

## 3. Current state

当前相关行为：

1. `create-spec-from-issue.yml` 在 issue 有 `ready-to-spec` 且 bot 已分配或被提及时创建 spec PR。
2. 该 workflow 的 job-level `if` 已经包含 `!contains(github.event.issue.labels.*.name, 'ready-to-implement')`，避免 issue 已经 ready to implement 时继续跑 spec。
3. `prepare_issue_spec_context.py` 的 `should_run()` 也在发现 `ready-to-implement` 时跳过，形成脚本级保护。
4. `create-implementation-from-issue.yml` 在 issue 有 `ready-to-implement` 且 bot 已分配或被提及时运行。
5. `prepare_issue_implementation_context.py` 已经能优先读取 `plan-approved` spec PR 的 head branch 作为 spec context。
6. 现有仓库没有专门响应 `plan-approved` label 的 workflow，也没有负责从 linked issue 移除 `ready-to-spec` 的脚本入口。

这些基础行为中，implementation 优先已经大体成立；缺口主要是 spec PR approval 后的状态同步和条件式 workflow dispatch。

## 4. Proposed changes

### 新增 plan-approved workflow

新增 `.github/workflows/plan-approved.yml`，专门处理 spec PR 上的 `plan-approved` label。

建议触发器：

```yaml
on:
  pull_request:
    types: [labeled]
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Spec pull request number"
        required: true
      agent_login:
        description: "Agent login that can be assigned; defaults to AGENT_LOGIN"
        required: false
        default: ""
```

job-level `if` 应保证：

- `pull_request` 事件只在 label 名称为 `plan-approved` 时运行。
- 只处理当前仓库内的 PR，避免 fork PR 触发有写权限的 issue 修改。
- workflow_dispatch 可以用于维护者手动重跑。

建议权限：

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: read
  actions: write
```

其中 `actions: write` 用于 dispatch `create-implementation-from-issue.yml`，`issues: write` 用于移除 issue label。

### 新增 approval context 脚本

新增 `.github/scripts/handle_plan_approved.py`，让 workflow step 尽量薄，只负责调用脚本和读取 outputs。

建议输入：

- `--repo`
- `--event-name`
- `--event-path`
- `--pr-number`
- `--agent-login`
- `--github-output`
- `--dry-run` 可选，便于单元测试或本地验证时禁用写操作。

建议职责：

1. 读取 PR 信息和 labels。
2. 验证 PR 带有 `plan-approved`。
3. 解析 linked issue number。
4. 读取 linked issue labels 和 assignees。
5. 如果 issue 有 `ready-to-spec`，调用 GitHub API 移除该 label。
6. 判断是否应触发 implementation：
   - issue labels 包含 `ready-to-implement`。
   - issue assignees 包含 `agent_login`。
7. 当应触发时，调用 `gh workflow run create-implementation-from-issue.yml --ref <default_branch> -f issue=<issue_number> -f agent_login=<agent_login>`。
8. 写入 GitHub outputs，例如 `issue_number`、`removed_ready_to_spec`、`implementation_dispatched`、`skip_reason`。

脚本应把 GitHub 内容视为数据，不应执行来自 issue 或 PR 文本的指令。

### linked issue 解析

建议实现一个独立函数 `resolve_linked_issue_number(pr: dict[str, Any]) -> int | None`，按以下顺序解析：

1. PR body 中的明确引用，例如 `Refs #57`、`Fixes #57`、`Closes #57`、`Issue #57`。
2. PR title 中的明确 issue number。
3. PR head branch fallback：`spec/issue-57`。

解析规则可以参考 `.github/scripts/write_spec_context.py` 中的 `issue_number_from_text()`，但 approval 脚本应避免把无关数字误判为 issue number。branch fallback 只接受 `spec/issue-<number>`。

### label 移除

移除 `ready-to-spec` 应使用 GitHub Issues API：

```text
DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/ready-to-spec
```

行为要求：

- 如果 label 存在并删除成功，记录 `removed_ready_to_spec=true`。
- 如果 label 不存在，视为幂等成功，记录 `removed_ready_to_spec=false`。
- 其他 API 错误应让 workflow 失败，因为状态同步没有完成。

### implementation dispatch

approval workflow 不应直接实现 issue，也不应修改 implementation branch。它只在条件满足时 dispatch 现有 workflow：

```text
gh workflow run create-implementation-from-issue.yml \
  --repo <repo> \
  --ref <default_branch> \
  -f issue=<issue_number> \
  -f agent_login=<agent_login>
```

dispatch 前应先完成 `ready-to-spec` 移除。这样 implementation workflow 看到的 issue 状态已经不再表示“需要 spec”。

不满足触发条件时，workflow 应成功结束并输出原因：

- `missing ready-to-implement`
- `missing bot assignee`
- `linked issue not found`
- `pull request is not a spec PR`

### 保持现有优先级保护

保留并测试现有两层保护：

- `.github/workflows/create-spec-from-issue.yml` job-level `if` 中的 `!contains(..., 'ready-to-implement')`。
- `.github/scripts/prepare_issue_spec_context.py` 中 labels 包含 `ready-to-implement` 时跳过。

如果后续实现发现 issue_comment 触发路径仍可能在 `ready-to-implement` 场景下跑 spec，应优先调整 workflow-level 条件或脚本 `should_run()`，不要通过删除 `ready-to-spec` 来掩盖触发顺序问题。

### 日志与 outputs

workflow 应输出足够信息便于维护者排查：

- linked issue number。
- 是否移除了 `ready-to-spec`。
- issue 是否已有 `ready-to-implement`。
- issue 是否分配给 bot。
- 是否 dispatch implementation。
- 未 dispatch 的具体原因。

不需要向 issue 写 comment，除非后续维护者希望有可见审计记录。本次范围以 workflow log 和 outputs 为主，避免增加 issue 噪音。

## 5. End-to-end flow

1. `create-spec-from-issue` 创建 `spec/issue-57` spec PR，PR body 包含 `Refs #57`。
2. 维护者 review spec PR 后添加 `plan-approved`。
3. `plan-approved.yml` 被 `pull_request.labeled` 触发。
4. workflow 调用 `handle_plan_approved.py`。
5. 脚本确认 PR 有 `plan-approved`，解析 linked issue 为 `57`。
6. 脚本读取 issue labels 和 assignees。
7. 脚本删除 issue 上的 `ready-to-spec`，如果不存在则幂等通过。
8. 如果 issue 有 `ready-to-implement` 且 assignee 包含 bot，脚本 dispatch `create-implementation-from-issue.yml`。
9. implementation workflow 运行后，`prepare_issue_implementation_context.py` 继续优先读取带 `plan-approved` 的 spec PR head branch。
10. 如果 issue 不满足实现条件，approval workflow 成功结束，只完成状态同步。

## 6. Risks and mitigations

- 风险：PR body 没有 linked issue，导致无法同步状态。
  - 缓解：支持 `spec/issue-<number>` branch fallback，并在无法解析时清晰输出 skip reason。
- 风险：误把非 spec PR 的 `plan-approved` 当作 spec approval。
  - 缓解：要求 PR head branch 或 changed files 能表明它是 `spec/issue-<number>` 规格 PR；否则跳过。
- 风险：`ready-to-spec` 移除失败但 implementation 已 dispatch。
  - 缓解：严格先删除 label，删除失败时不 dispatch。
- 风险：重复添加或重跑 `plan-approved` 导致重复 dispatch implementation。
  - 缓解：workflow concurrency 使用 PR number；脚本幂等删除 label。若需要进一步防重复，可在 dispatch 前检查目标 implementation branch 是否已有 open PR，但本规格不要求阻断现有 implementation workflow 的幂等保护。
- 风险：`agent_login` 未配置时无法判断 bot assignee。
  - 缓解：缺少 agent login 时只移除 `ready-to-spec`，不 dispatch implementation，并输出 `missing agent login`。
- 风险：workflow_dispatch 权限或 workflow 文件名变化导致 dispatch 失败。
  - 缓解：把 dispatch 失败视为 workflow 失败，避免维护者误以为实现已启动。

## 7. Testing and validation

新增或更新测试时，应优先覆盖脚本函数，减少对 live GitHub API 的依赖。

建议新增 `tests/test_handle_plan_approved.py`：

- 从 PR body `Refs #57` 解析 linked issue。
- 从 branch `spec/issue-57` fallback 解析 linked issue。
- 无 linked issue 时返回 skip。
- issue 有 `ready-to-spec` 时调用 label removal。
- issue 没有 `ready-to-spec` 时幂等成功。
- issue 有 `ready-to-implement` 且 assignee 包含 bot 时 dispatch implementation。
- issue 缺少 `ready-to-implement` 时不 dispatch。
- issue 缺少 bot assignee 时不 dispatch。
- `agent_login` 为空时不 dispatch。
- 非 `plan-approved` label 或非 spec PR 时跳过。

建议更新或补充现有测试：

- 覆盖 `.github/scripts/prepare_issue_spec_context.py` 中 `ready-to-implement` 优先跳过 spec 的行为。
- 覆盖 `.github/scripts/prepare_issue_implementation_context.py` 继续优先选择 `plan-approved` spec PR head branch。

建议人工验证：

```bash
python3 -m unittest tests.test_handle_plan_approved
python3 -m unittest discover -s tests
```

GitHub workflow 验证：

- 在测试 issue 上创建 spec PR。
- 给 issue 保留 `ready-to-spec`，不给 `ready-to-implement`，给 spec PR 添加 `plan-approved`，确认只移除 `ready-to-spec`。
- 再创建一个 issue，使其在 approval 前已有 `ready-to-implement` 且 bot 已分配，添加 `plan-approved` 后确认 implementation workflow 被 dispatch。
- 确认 spec PR 未 merge 时，implementation context 使用该 approved PR head branch 的 specs。

## 8. Follow-ups

- 可选增加 issue comment 审计记录，说明 `plan-approved` 已移除 `ready-to-spec`，以及是否启动 implementation。
- 可选在 implementation dispatch 前检查是否已有 open implementation PR，进一步减少重复运行。
- 可选把 linked issue 解析 helper 从 `write_spec_context.py` 抽出为共享模块，避免多个脚本维护相近正则。
