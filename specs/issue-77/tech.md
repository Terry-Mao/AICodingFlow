# 技术规格：实现 PR Bot `/review` 指令

## 1. Problem

当前 `.github/workflows/review-pr.yml` 已有 `issue_comment` trigger，但入口条件依赖 `@AGENT_LOGIN` mention，并且 `.github/scripts/resolve_pr_event.py` 在 `issue_comment` 场景下把 open draft PR 也视为 `reviewable`。issue 77 要求新增 `/review` 指令，且必须是 PR 下的 body-level comment，并且 PR 必须是非 draft 状态。

技术目标是复用现有 AI PR Review workflow，同时把 comment 触发条件从 mention 子串匹配调整为明确的 `/review` command 解析，并修正 comment-trigger draft gate。

## 2. Relevant code

- `.github/workflows/review-pr.yml` — AI PR Review workflow。当前 `on.issue_comment.types` 已包含 `created`，`preflight.if` 中用 `contains(github.event.comment.body, format('@{0}', vars.AGENT_LOGIN))` 允许 PR comment mention 触发。
- `.github/scripts/resolve_pr_event.py` — 将 `pull_request`、`issue_comment`、`workflow_dispatch` 事件规范化为 PR payload，并通过 `review_state()` 输出 `reviewable`、`draft`、`head_repo` 等状态。当前 `issue_comment` 会调用 `gh api repos/{repo}/pulls/{number}` 获取 PR。
- `.github/scripts/select_review_skill.py` — 根据 `pr_diff.txt` changed files 选择 `.agents/skills/review-spec-repo/SKILL.md` 或 `.agents/skills/review-pr-repo/SKILL.md`，`/review` 应继续复用该逻辑。
- `tests/test_review_workflow_dispatch.py` — 覆盖 `review-pr.yml` trigger、job gate、preflight/review job 结构和 workflow dispatch 行为。
- `tests/test_resolve_pr_event.py` — 覆盖 PR event 解析、issue_comment 拉取 PR payload、reviewable 状态计算。需要更新 draft comment trigger 期望。
- `README.md` — 当前说明“需要重新 review 时，在非 draft PR comment 中 `@AGENT_LOGIN` 或使用手动 workflow dispatch”，应在实现阶段改为描述 `/review`。

## 3. Current state

现有 AI PR Review 流程：

1. `review-pr.yml` 在 `pull_request`、`workflow_dispatch` 或 `issue_comment` 事件中启动。
2. `preflight.if` 对 `issue_comment` 只确认它是 PR comment、`AGENT_LOGIN` 非空、comment body 包含 `@AGENT_LOGIN`。
3. `resolve_pr_event.py` 对 `issue_comment` 读取 event issue number，并通过 GitHub API 拉取 PR payload。
4. `review_state()` 对 `issue_comment` 设置 `manual_comment_trigger = True`，导致 open draft PR 也返回 `reviewable: true`。
5. review job checkout PR head，生成 `pr_description.txt` 和 `pr_diff.txt`，选择 review skill，运行 Codex，校验并发布 review。

当前限制：

- 没有 `/review` command parser。
- mention 子串匹配不区分 body-level command、quoted text 或代码块。
- comment-trigger draft PR 会被视为可 review，与 issue 77 的“非 draft 状态”要求冲突。
- README 与测试描述的是 `@AGENT_LOGIN` 手动触发，而不是 `/review`。

## 4. Proposed changes

### 增加 command parser

在 `.github/scripts/resolve_pr_event.py` 中新增可单元测试的 helper：

```python
def comment_has_review_command(body: str) -> bool:
    ...
```

建议规则：

- 按行扫描 comment body。
- 忽略 fenced code block 内的内容。遇到以 optional whitespace 后的 triple backticks 开始的行时切换 code block 状态。
- 忽略 quoted line：`line.lstrip().startswith(">")`。
- 对非 quoted、非 code block 行执行 `line.strip() == "/review"`。
- 只要找到一行精确 `/review`，返回 `True`。
- 非字符串、空字符串或只有空白时返回 `False`。

该 parser 应避免使用简单 `contains("/review")`，否则会误触发普通段落、历史引用或代码示例。

### 在 workflow gate 中使用 `/review`

更新 `.github/workflows/review-pr.yml` 的 `preflight.if`：

- 保留 `issue_comment` trigger。
- 对 `issue_comment` 分支继续要求 `github.event.issue.pull_request != null`。
- 将 `@AGENT_LOGIN` mention 条件替换为轻量 `/review` 条件。

由于 GitHub Actions expression 不适合完整解析 quoted text 和 fenced code block，workflow gate 可以只做粗筛，例如要求 `contains(github.event.comment.body, '/review')`。精确 body-level command 判断应放在 `resolve_pr_event.py` 中，避免 YAML expression 过度复杂。

如果实现希望在 YAML 层避免大部分误触发，可以把 `contains` 保留为粗筛；最终是否 review 必须由 Python preflight 输出 `reviewable` 决定。

### 在 `resolve_pr_event.py` 中加入精确 comment gate

调整 `resolve_event()` 或 `review_state()` 的数据流，使 `issue_comment` 场景下可以判断原始 comment body：

- `resolve_event()` 对 `issue_comment` 仍确认 `issue.pull_request` 存在。
- 在 fetch PR 前或 fetch PR 后检查 `comment_has_review_command(event.get("comment", {}).get("body", ""))`。
- 如果没有有效 `/review` command，可以返回带 `pull_request` payload 的 event 并让 `review_state()` 输出 `reviewable: false`，也可以在不需要 PR payload 的情况下构造 skip 状态。推荐保持现有 output shape，尽量少改 workflow。
- 为了让 workflow 日志更清晰，可以新增输出字段 `skip_reason`，但这不是本 issue 的必须项。

推荐较小改动：

1. 让 `resolve_event()` 对 `issue_comment` 返回：

```python
{
    "pull_request": fetch_pr(...),
    "comment": {"body": "..."},
    "review_command": True | False,
}
```

2. 让 `review_state(event, repo, event_name)` 在 `issue_comment` 时要求 `event.get("review_command") is True`。

### 修正 draft gate

调整 `review_state()`：

- `pull_request` event：继续要求 open、非 draft。
- `issue_comment` event：要求 open、非 draft、且 `review_command` 为 true。
- `workflow_dispatch`：可保持现有行为，或继续由 resolver 判定 open 状态；不要因为 `/review` 改动破坏手动 dispatch。

建议规则：

```python
is_open = state == "open"
is_draft = bool(pr.get("draft"))
is_comment_review = event_name == "issue_comment" and event.get("review_command") is True
reviewable = is_open and (not is_draft or event_name == "workflow_dispatch") and (
    event_name in {"pull_request", "workflow_dispatch"} or is_comment_review
)
```

如果维护者希望 `workflow_dispatch` 也拒绝 draft PR，应作为独立产品决定；本 issue 只明确 `/review` 的非 draft 前提。PR event 的非 draft gate 已在 workflow YAML 中存在。

### 保持 review 执行路径不变

`/review` 不需要新增 review job 或新的 skill：

- `Snapshot PR description` 仍使用规范化 PR event。
- `Snapshot PR diff` 仍基于 base/head sha。
- `Select review skill` 仍使用 `select_review_skill.py`。
- `spec_context.md` 只在 code PR review skill 需要时生成。
- `Run AI review` prompt 不需要知道触发方式。
- `validate_review_json.py` 与 `post_pr_review.py` 不需要为 `/review` 做特殊分支。

### 更新文档和测试

实现阶段应更新：

- `tests/test_review_workflow_dispatch.py`
  - 断言 `issue_comment` trigger 仍存在。
  - 断言 workflow gate 不再依赖 `@AGENT_LOGIN`，而是包含 `/review` comment 粗筛或对应步骤。
  - 保留 `pull_request`、`workflow_dispatch`、preflight/review job 结构断言。
- `tests/test_resolve_pr_event.py`
  - 新增 `comment_has_review_command()` 用例。
  - 更新 `test_review_state_allows_manual_comment_review_for_draft_same_repo_pr`，改为 draft comment 不可 review。
  - 新增 open non-draft PR + valid `/review` 可 review。
  - 新增 invalid comment body 不可 review。
  - 保留普通 issue comment 被拒绝。
- `README.md`
  - 将“PR comment 中 `@AGENT_LOGIN` 手动触发”更新为“在非 draft PR 的普通 body-level comment 中发送 `/review`”。

## 5. End-to-end flow

1. 用户在 PR conversation 中创建 comment，body 包含有效 body-level `/review`。
2. GitHub 触发 `issue_comment` workflow。
3. `preflight.if` 确认事件是 PR comment，并通过轻量 `/review` 粗筛。
4. `resolve_pr_event.py` 读取 event，确认 `issue.pull_request` 存在，并解析 comment body。
5. 脚本通过 GitHub API 拉取 PR payload。
6. `review_state()` 确认 PR 是 open、非 draft，且 comment 有有效 `/review` command。
7. `preflight` 输出 `reviewable=true`。
8. review job 复用现有流程重新生成快照、选择 skill、运行 Codex review、校验并发布 PR review。

## 6. Risks and mitigations

- 风险：YAML `contains('/review')` 粗筛仍会让部分无效 comment 进入 preflight。
  - 缓解：Python parser 负责最终 body-level command 判断，preflight 输出 `reviewable=false` 后 review job 不运行。
- 风险：简单 parser 误识别 quoted text 或 fenced code block。
  - 缓解：为 quoted line、code fence、普通句子和带参数命令写单元测试。
- 风险：修正 draft gate 改变了现有 mention comment 可 review draft PR 的行为。
  - 缓解：issue 明确要求 `/review` 前提是非 draft；测试应把 draft comment 场景固定为 skip。
- 风险：删除 `@AGENT_LOGIN` mention 触发会影响已有用户习惯。
  - 缓解：产品规格把是否保留 mention 作为开放问题；实现可以在不削弱 `/review` 行为的前提下兼容 mention，但默认文档应引导使用 `/review`。
- 风险：Actions expression 过度复杂导致 workflow 难维护。
  - 缓解：YAML 只做轻量条件，复杂 command 解析放在 Python helper 中。

## 7. Testing and validation

建议运行：

```bash
python3 -m unittest tests.test_resolve_pr_event tests.test_review_workflow_dispatch
python3 -m unittest discover -s tests
```

重点覆盖：

- `comment_has_review_command("/review") == True`。
- 前后空白和空白行不影响有效 `/review`。
- `> /review` 不触发。
- fenced code block 中的 `/review` 不触发。
- `please /review` 和 `/review now` 不触发。
- issue_comment + open non-draft PR + valid `/review` 返回 `reviewable=true`。
- issue_comment + draft PR + valid `/review` 返回 `reviewable=false`。
- issue_comment + closed PR + valid `/review` 返回 `reviewable=false`。
- issue_comment + invalid command 返回 `reviewable=false`。
- 普通 issue comment 仍被拒绝为非 PR comment。
- workflow YAML 仍有 `issue_comment` trigger，且 review job 仍依赖 preflight 输出。

## 8. Follow-ups

- 设计统一 Bot command parser，供未来 `/spec`、`/implement` 或其他指令复用。
- 如需权限控制，可新增 author association gate，例如只允许 member / collaborator / owner 触发 `/review`。
- 如需兼容更多命令语法，可单独设计 `/review` 参数，例如 `/review full` 或 `/review spec`。
