# 技术规格：修正本地 review base 选择

## 1. Problem

`.github/scripts/prepare_local_review_inputs.py` 当前在 `main()` 中先通过 `args.base or default_base()` 解析本地 diff base，再尝试通过 `gh pr view` 获取当前分支的 PR event。这样即使当前分支已有 PR，脚本也仍然用本地默认 base 生成 `pr_diff.txt`。

当本地 `upstream/main` stale 而 PR 实际 base 是更新的 `origin/main` 或某个 PR `baseRefOid` 时，本地 `review-pr-local` / `review-spec-local` 会生成比 CI 更大的 diff。CI workflow 已经从 PR event 输出 `base_sha`，并用该 SHA 调用 `build_pr_diff.py`；本地脚本应尽量复用同一 PR base SHA 语义。

## 2. Relevant code

- `.github/scripts/prepare_local_review_inputs.py:112` — `default_base()` 当前按 `upstream/main`, `origin/main`, `main` 顺序选择 fallback base。
- `.github/scripts/prepare_local_review_inputs.py:185` — `github_pr_event()` 已通过 `gh pr view` 获取 `baseRefOid`、`headRefOid`、`baseRefName`、`headRefName` 并构造成 PR event。
- `.github/scripts/prepare_local_review_inputs.py:217` — `github_pr_event_for_current_branch()` 在 GitHub CLI 失败、JSON 解析失败或命令失败时返回 `None`。
- `.github/scripts/prepare_local_review_inputs.py:319` — `main()` 当前先解析 `base` / `base_sha`，再选择 GitHub PR event 或 local fallback event。
- `.github/scripts/prepare_local_review_inputs.py:268` — `write_local_diff(base_sha, output)` 使用传入的 `base_sha` 生成本地工作区 snapshot diff。
- `.agents/skills/review-pr-local/SKILL.md` 和 `.agents/skills/review-spec-local/SKILL.md` — 两个 local review skill 都调用同一个准备脚本。
- `.github/workflows/review-pr.yml:131` — CI review 使用 `steps.pr.outputs.base_sha` 作为 `build_pr_diff.py --base`，该值来自 PR event。
- `.github/scripts/resolve_pr_event.py:132` — CI preflight 输出 PR event 中的 `base.sha` 和 `head.sha`。
- `tests/test_prepare_local_review_inputs.py` — 当前覆盖本地输入生成、GitHub PR description 优先、fallback 行为、local worktree diff 和 baseline status。

## 3. Current state

本地脚本当前流程：

1. 删除 stale review artifacts。
2. 解析 repo。
3. 设置 `base = args.base or default_base()`。
4. `base_sha = resolve_ref(base)`。
5. `head_sha = resolve_ref(args.head)`。
6. `event = github_pr_event_for_current_branch(repo) or local_pr_event(repo, base, base_sha, head_sha)`。
7. 写 `pr_description.txt`。
8. 用 `base_sha` 写 `pr_diff.txt`。

这个顺序导致 GitHub PR event 只影响 `pr_description.txt`，不影响 `pr_diff.txt` 的 base。已有测试 `test_prefers_github_pr_description_over_local_description_only` 也固定了当前行为：即使有 GitHub PR event，仍断言 `default_base()` 被调用并且 `local_worktree_diff()` 使用本地 default base。

## 4. Proposed changes

### 调整 base 解析顺序

在 `main()` 中把 PR event 获取提前到 base 决策之前：

1. 删除 stale files。
2. 解析 repo。
3. 解析 head SHA。
4. 若未传 `--base`，尝试 `github_pr_event_for_current_branch(repo)`。
5. 根据优先级选择 base：
   - `args.base` 存在：使用显式 base，`base_sha = resolve_ref(args.base)`。
   - 否则 GitHub PR event 存在且 `event["pull_request"]["base"]["sha"]` 非空：使用该 SHA，`base_sha = base sha`，`base` 可使用 base ref 或 SHA 的展示值。
   - 否则：使用 `default_base()`，并 `resolve_ref(base)`。
6. 如果没有 GitHub PR event，构造 `local_pr_event(repo, base, base_sha, head_sha)`。
7. 如果有 GitHub PR event，但使用了显式 `--base`，应更新 event 中 `pull_request.base.sha` 和 `pull_request.base.ref`，或重新构造一致的 local event，避免 `pr_description.txt` 与实际 diff base 不一致。
8. 写 description、diff、skill selection、spec context 和 baseline status。

推荐新增小 helper，降低 `main()` 分支复杂度：

```python
def pr_base_sha(event: dict[str, Any] | None) -> str:
    if not event:
        return ""
    return str(((event.get("pull_request") or {}).get("base") or {}).get("sha") or "")
```

也可以新增 `choose_review_base(args_base, event)`，但保持脚本简单更符合当前风格。

### 保持显式 `--base` 最高优先级

`--base` 是用户的显式指令，应继续覆盖所有自动推断。实现时不要在 `args.base` 存在时调用 PR base SHA 覆盖它。

当 `args.base` 存在且 GitHub PR event 也存在时，建议在写 `pr_description.txt` 前让 event base 反映显式 base：

- `event["pull_request"]["base"]["ref"] = display_base_ref(args.base)`
- `event["pull_request"]["base"]["sha"] = base_sha`

这样 root snapshot 中的 `Base: ... @ ...` 与 `pr_diff.txt` 实际 base 保持一致。

### 使用 PR base SHA 时的展示值

当使用 GitHub PR event 的 `baseRefOid` 时：

- `base_sha` 直接取 PR event base SHA，不需要 `resolve_ref()`。
- `base` 用 PR event 的 `base.ref` 作为展示值和 output 中的 `base` 值。
- 若 base ref 为空，可用 base SHA 作为 `base` output。

这与 CI 行为一致：CI fetch 并使用 PR event base SHA，而不是依赖本地 remote ref 当前指向。

### 调整 fallback 默认 base 顺序

修改 `default_base()`：

```python
for ref in ("origin/main", "upstream/main", "main"):
    ...
```

该调整只影响没有显式 `--base` 且没有可用 PR base SHA 的场景。

### 不自动 fetch

本 issue 不要求本地脚本自动 fetch PR base SHA。`local_worktree_diff()` 底层 `git diff` 需要 base object 可用；如果 PR base SHA 本地缺失，保持命令失败即可。未来如需自动 fetch，应另行设计，因为那会引入网络、remote 和认证行为。

### 保持其他行为不变

不要改动：

- `local_worktree_diff()` 对 committed/staged/unstaged/untracked/deleted/renamed files 的 snapshot 语义。
- `select_review_skill.py` 的 spec-only 判断。
- `write_spec_context_if_needed()` 的 code review spec context 行为。
- `.local_review_baseline.status` 写入和 local review result validation。
- `review-pr-local` / `review-spec-local` skill 的用户命令。

## 5. End-to-end flow

### 当前分支已有 PR

1. 用户运行 `review-pr-local` 或 `review-spec-local` 准备命令。
2. `prepare_local_review_inputs.py` 读取当前分支，并通过 `gh pr view` 获取 PR metadata。
3. 脚本从 PR event 取 `pull_request.base.sha`。
4. 脚本基于该 base SHA 和本地工作区快照生成 `pr_diff.txt`。
5. `pr_description.txt` 显示同一个 base SHA。
6. 后续 skill selection、Codex review 和 validation 继续按现有流程执行。

### 当前分支没有可解析 PR

1. `gh pr view` 失败或返回不可用数据。
2. 脚本使用 `args.base` 或 fallback `default_base()`。
3. fallback 默认优先 `origin/main`。
4. 脚本构造 local PR event，并用同一个 base SHA 写 description 和 diff。

### 显式 `--base`

1. 用户传入 `--base origin/main` 或其他 ref/SHA。
2. 脚本解析该 base。
3. 即使当前分支有 GitHub PR，diff 仍使用用户指定 base。
4. `pr_description.txt` 中的 base 与用户指定 base 保持一致。

## 6. Risks and mitigations

- 风险：当前测试固定了 GitHub PR event 只影响 description 的旧行为。
  - 缓解：更新测试期望，明确已有 PR 时 `default_base()` 不应被调用，`local_worktree_diff()` 应使用 PR base SHA。
- 风险：PR base SHA 在本地对象库中不存在会导致 `git diff` 失败。
  - 缓解：保持失败可见；本规格不引入自动 fetch。用户可先 fetch 或显式传入可用 `--base`。
- 风险：显式 `--base` 与 PR metadata 同时存在时 description 和 diff 不一致。
  - 缓解：实现时同步 event base 字段，或在显式 base 场景使用 local event。
- 风险：改变 fallback 顺序可能影响依赖 `upstream/main` 的个人工作流。
  - 缓解：`--base upstream/main` 继续可用；该 repo 中 `origin` 和 `upstream` 常指向同一 URL，优先 `origin/main` 更符合本地分支 PR 工作流。
- 风险：过度重构 `main()` 影响 local review snapshot 的其他行为。
  - 缓解：保持改动集中在 base 选择和 event base 一致性，依靠现有 local worktree diff tests 防回归。

## 7. Testing and validation

更新 `tests/test_prepare_local_review_inputs.py`：

- 新增或更新已有 PR 场景：
  - `github_pr_event_for_current_branch()` 返回 base SHA `github-base`。
  - 未传 `--base`。
  - 断言 `default_base()` 未调用。
  - 断言 `local_worktree_diff()` 或 `write_local_diff()` 使用 `github-base`。
  - 断言 `pr_description.txt` 中包含 `Base: main @ github-base`。
- 新增显式 `--base` 场景：
  - GitHub PR event 存在。
  - 传入 `--base origin/main`。
  - 断言 diff 使用 resolved `origin/main` SHA，而不是 `github-base`。
  - 断言 description base 与显式 base 一致。
- 新增 PR event base SHA 为空场景：
  - GitHub PR event 存在但 base sha 为空。
  - 断言 fallback 使用 `default_base()`。
- 新增 `default_base()` 顺序测试：
  - mock `optional_git()` 让 `origin/main` 和 `upstream/main` 都存在。
  - 断言返回 `origin/main`。
  - 覆盖只有 `upstream/main`、只有 `main`、都不存在时的行为。
- 保留现有 tests：
  - code review/spec review skill selection。
  - stale files cleanup。
  - local worktree diff 包含 committed、staged、unstaged、deleted、untracked。
  - ignored files 不进入 diff。
  - rename snapshot。
  - empty diff 报错。
  - baseline status。

建议验证命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_prepare_local_review_inputs
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

## 8. Follow-ups

- 如后续需要进一步贴近 CI，可设计显式 opt-in 的 `--fetch-base`，在本地缺少 PR base object 时 fetch base SHA。
- 可考虑在输出中增加 `base_source`，例如 `explicit`, `github-pr`, `default`，帮助排查本地 review 使用了哪个 base 来源。
- 可单独评估 stale remote 检测：当 `origin` 和 `upstream` 指向同一 GitHub repo 且两个 ref 都存在时，提示用户 stale ref，而不是自动修改 remote state。
