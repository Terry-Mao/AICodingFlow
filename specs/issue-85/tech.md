# 技术规格：让本地 review 支持 dirty worktree

## 1. Problem

`review-pr-local` 和 `review-spec-local` 都通过 `.github/scripts/prepare_local_review_inputs.py` 生成本地 review 快照。该脚本当前在准备阶段调用 `require_clean_worktree()`，只要 `git status --porcelain=v1 -z` 有任何输出就直接退出。这使本地 review 只能在工作区干净时运行，无法满足 issue 85 中“先 review 完再 commit”的工作流。

技术目标是移除准备阶段对干净工作区的硬性要求，并让本地 `pr_diff.txt` 基于当前工作区相对 base 的完整内容生成，同时保留 review 阶段不得修改业务文件的安全校验。

## 2. Relevant code

- `.agents/skills/review-pr-local/SKILL.md` — 本地代码 PR review skill。第 1 步调用 `.github/scripts/prepare_local_review_inputs.py --expected-skill .agents/skills/review-pr-repo/SKILL.md`，第 8 步调用 `.github/scripts/validate_local_review_result.py`。
- `.agents/skills/review-spec-local/SKILL.md` — 本地 spec review skill。结构与 `review-pr-local` 相同，但期望 skill 为 `.agents/skills/review-spec-repo/SKILL.md`。
- `.github/scripts/prepare_local_review_inputs.py` — 本地 review 输入准备入口。当前 `main()` 会先 `remove_stale_review_files()`，再调用 `require_clean_worktree()`，之后用 `write_diff(base_sha, head_sha, Path("pr_diff.txt"))` 生成 diff。
- `.github/scripts/build_pr_diff.py` — 把 Git diff 转换为 review 使用的文本格式。当前由 `prepare_local_review_inputs.py` 复用。
- `.github/scripts/select_review_skill.py` — 根据 `pr_diff.txt` changed files 选择 spec review 或 code review skill。
- `.github/scripts/write_spec_context.py` — 对 code review 需要时从 diff changed files 解析 spec context。
- `.github/scripts/validate_local_review_result.py` — review 后校验只允许 `pr_description.txt`、`pr_diff.txt`、`spec_context.md`、`review.json` 出现未 staged 改动。
- `tests/test_prepare_local_review_inputs.py` — 覆盖本地 review 快照生成、旧快照清理、expected skill 校验、`.gitignore` 规则和 remote URL 解析。
- `tests/test_validate_local_review_result.py` — 覆盖本地 review 阶段允许和拒绝的文件变化。

## 3. Current state

当前本地 review 准备流程：

1. 删除旧的 `pr_description.txt`、`pr_diff.txt`、`spec_context.md`、`review.json`。
2. 调用 `require_clean_worktree()` 检查 `git status --porcelain=v1 -z`。
3. 工作区有任何 staged、unstaged 或 untracked 变化时退出，并提示 `working tree must be clean before local review`。
4. 解析 repo、base、base sha、head sha 和本地 PR event。
5. 用 `build_pr_diff.run_git_diff(base_sha, head_sha, 3)` 生成 `base...HEAD` 的 committed diff。
6. 根据 diff 选择 review skill，并按需生成 `spec_context.md`。

当前限制：

- 未提交修改永远无法进入 `pr_diff.txt`。
- 未跟踪新文件无法被本地 review 覆盖。
- 本地 review 的使用时机被迫移动到 commit 之后。
- `validate_local_review_result.py` 已经负责 review 阶段的写入边界，因此准备阶段的 clean worktree gate 过于严格。

## 4. Proposed changes

### 移除准备阶段 clean worktree gate

- 删除或停用 `prepare_local_review_inputs.py` 中 `require_clean_worktree()` 的调用。
- 可以保留 helper 供未来其他入口使用，但本地 review 准备流程不应再调用它。
- `review-pr-local` 和 `review-spec-local` skill 文档应更新为说明本地 review 支持 dirty worktree，并强调 review 阶段仍不得修改业务文件。

### 生成当前工作区 diff

在 `prepare_local_review_inputs.py` 中新增本地 diff 生成路径，替代只比较 `base_sha` 与 `head_sha` 的逻辑。建议新增可测试 helper：

```python
def local_worktree_diff(base_sha: str, context_lines: int) -> list[str]:
    ...
```

建议实现方式：

- 继续使用 Git 生成 unified diff，再交给 `build_pr_diff.convert()` 转成现有 review 文本格式。
- 对 tracked file 的 committed、staged、unstaged 当前状态，以及 tracked file deletion，使用能比较 `base_sha` 与工作区最终内容的 diff 方式。
- 对 untracked file，使用 Git 规则枚举未被 ignore 的 untracked 文件，并把它们作为新增文件纳入 diff。
- 排除根目录临时 review 输出文件：
  - `pr_description.txt`
  - `pr_diff.txt`
  - `spec_context.md`
  - `review.json`
- 保持现有 context line 参数 `3`。

一种可行方案是：

1. 枚举 dirty / untracked 路径，过滤 `TEMP_REVIEW_PATHS`。
2. 在临时 index 中构造“当前工作区快照”，避免修改用户真实 index。
3. 将 `HEAD` tree 读入临时 index，再把 tracked working tree 文件和非 ignored untracked 文件加入该临时 index。
4. 对工作区中已删除的 tracked 文件，在临时 index 中执行等价 remove 操作，确保删除也进入快照。
5. 对临时 index 执行 `git diff --cached --unified=3 <base_sha>`，得到 base 到当前工作区快照的 diff。

该方案的优点是可以同时覆盖 committed、staged、unstaged、untracked 和 deleted 内容，并且不需要 stash、commit 或改动真实 index。实现时应通过 `GIT_INDEX_FILE` 指向临时 index，并确保临时文件在异常时清理。

如果实现选择其他 Git 组合命令，也必须满足同样语义：`pr_diff.txt` 代表当前工作区最终文件状态相对 base 的完整变化，不改变真实 index，不漏掉 untracked 文件，不包含 review 快照文件。

### 空 diff 处理

- 如果生成的 diff 为空，`prepare_local_review_inputs.py` 应以清晰错误退出，例如 `no local changes to review against <base>`。
- 空 diff 不应继续选择 review skill 或生成误导性的 `review.json`。
- 如果只有根目录临时 review 输出变化，过滤后也应视为空 diff。

### 保持 skill 选择和 spec context 流程

- `write_diff()` 可以调整为接收已经生成的 raw diff，或新增 `write_local_diff(base_sha, output)`。
- `select_review_skill.select_skill(pr_diff_text)` 继续从转换后的 `pr_diff.txt` 判断是 spec review 还是 code review。
- `write_spec_context_if_needed()` 继续使用 converted diff text 的 changed files。
- `local_pr_event()` 可以继续使用 `head_sha = resolve_ref(args.head)` 表示当前 `HEAD`，但 PR diff 快照必须来自工作区内容。PR description 中的 head sha 仍可用于描述当前分支提交点。

### 保持 review 阶段安全边界

- `validate_local_review_result.py` 的职责不变：review 阶段结束后，只允许 root-level review 输出文件处于 unstaged changed / untracked 状态。
- 不要放宽 validator 对业务文件改动的拒绝。
- 因为准备阶段本身会在 dirty worktree 中运行，`validate_local_review_result.py` 不能简单把所有已有业务文件 dirty 状态视为 review 阶段新增问题。实现需要在 local review skill 或准备脚本中建立 baseline。

推荐实现：

1. `prepare_local_review_inputs.py` 在生成快照后记录一次 baseline status，内容来自 `git status --porcelain=v1 -z --untracked-files=all`，并排除允许的 review 输出文件。
2. baseline 写入固定 root 文件 `.local_review_baseline.status`，并加入 `.gitignore` 和 workflow 临时文件过滤，避免误提交。
3. 固定路径由准备脚本覆盖写入；下次本地 review 可以覆盖旧 baseline，不需要单独清理脚本。
4. 更新 local review skill 文档，让第 8 步固定调用 `validate_local_review_result.py --baseline-status .local_review_baseline.status`，避免模型解析 stdout 中的随机临时路径。
5. `validate_local_review_result.py` 在提供 baseline 时比较“准备后状态”和“review 后状态”：允许 baseline 中已经存在的业务文件 dirty 状态继续存在，但拒绝新增业务文件改动、删除、新增 staged change，或已有业务文件状态发生变化。
6. validator 运行结束后可以删除 `.local_review_baseline.status`；异常路径下残留也应被 `.gitignore` 和临时文件过滤规则排除。

该方案会在 repository root 多一个受控临时文件，但路径固定、可覆盖、可忽略，避免跨 skill 手动传递 `/tmp` 随机路径的脆弱性。baseline 使用 status 级比较是有意的轻量取舍：它防止 review 阶段新增或改变文件状态，但不承诺检测 review 前已经 dirty 的业务文件内容是否再次变化。

### 更新本地 review skill 文档

实现阶段应更新：

- `.agents/skills/review-pr-local/SKILL.md`
- `.agents/skills/review-spec-local/SKILL.md`

文档应说明：

- 本地 review 可以在未提交修改存在时运行。
- 准备阶段会基于当前工作区生成快照。
- review 阶段仍只能写 `review.json` 和准备脚本生成的快照文件。
- 校验阶段使用固定 `.local_review_baseline.status` baseline 文件。
- 不会自动 stage、commit、stash 或 push。

## 5. End-to-end flow

1. 开发者在本地工作区保留未提交修改。
2. 开发者运行 `review-pr-local` 或 `review-spec-local`。
3. skill 调用 `.github/scripts/prepare_local_review_inputs.py`。
4. 脚本清理旧 review 快照，但不再要求业务工作区干净。
5. 脚本解析 base 与 head，并生成 base 到当前工作区快照的 diff。
6. 脚本写入 `pr_description.txt` 和 `pr_diff.txt`，按 diff 选择 review skill。
7. 如果是 code review 且需要 spec context，脚本写入 `spec_context.md`。
8. review skill 读取快照并写入 `review.json`。
9. `validate_local_review_result.py` 校验 review 阶段没有越权修改业务文件。

## 6. Risks and mitigations

- 风险：dirty worktree diff 漏掉 untracked 文件。
  - 缓解：使用 Git ignore 规则枚举未跟踪文件，并为新增文件写单元测试。
- 风险：dirty worktree diff 漏掉 tracked file deletion，导致 `pr_diff.txt` 不能代表当前工作区最终状态。
  - 缓解：构造临时 index 时对已删除 tracked 文件执行 remove，并增加删除文件的 diff 生成测试。
- 风险：实现时修改真实 index，影响用户 staging 状态。
  - 缓解：使用 `GIT_INDEX_FILE` 临时 index；测试确认真实 staged 状态不被命令改变。
- 风险：review 快照文件被纳入 `pr_diff.txt`，导致自我 review 或 skill 选择错误。
  - 缓解：在 diff 路径过滤中显式排除 `TEMP_REVIEW_PATHS`，并加测试。
- 风险：dirty worktree 下 validator 无法区分“review 前已有业务改动”和“review 阶段新增业务改动”。
  - 缓解：实施时引入固定 root baseline 文件 `.local_review_baseline.status`，并通过 `.gitignore` 和临时文件过滤防止误提交。
- 风险：status 级 baseline 无法发现 review 前已经 dirty 的业务文件内容被再次修改。
  - 缓解：接受该轻量取舍，当前目标是避免新增或状态变化的越权改动；如果后续误改风险变高，再升级为内容 hash 或 diff 快照 baseline。
- 风险：本地 review 输出与 CI review 输出语义不同。
  - 缓解：这是预期差异；本地 review 面向当前工作区，CI review 面向 PR committed diff。文档中明确区分。
- 风险：工作区包含无关本地改动，review 结果噪声变大。
  - 缓解：不自动选择文件；由用户在运行本地 review 前整理工作区。未来可设计 staged-only 或 path filter。

## 7. Testing and validation

建议运行：

```bash
python3 -m unittest tests.test_prepare_local_review_inputs tests.test_validate_local_review_result
python3 -m unittest discover -s tests
```

重点新增或更新测试：

- `prepare_local_review_inputs.main()` 不再调用会拒绝 dirty worktree 的 gate。
- committed-only diff 仍能生成与现有逻辑等价的 `pr_diff.txt`。
- unstaged tracked file 修改会出现在 `pr_diff.txt`。
- staged tracked file 修改会出现在 `pr_diff.txt`，且真实 index 不被改变。
- deleted tracked file 会作为删除 diff 出现在 `pr_diff.txt`。
- untracked 且未被 ignore 的文件会作为新增文件出现在 `pr_diff.txt`。
- ignored untracked 文件不会出现在 `pr_diff.txt`。
- 根目录 `pr_description.txt`、`pr_diff.txt`、`spec_context.md`、`review.json` 不会出现在 `pr_diff.txt`。
- `.local_review_baseline.status` 写入固定 root 路径、被 `.gitignore` 忽略、不会出现在 `pr_diff.txt`。
- 纯 `specs/` dirty diff 仍选择 `.agents/skills/review-spec-repo/SKILL.md`。
- 非纯 `specs/` dirty diff 仍选择 `.agents/skills/review-pr-repo/SKILL.md`。
- 空 diff 会以明确错误退出。
- validator 在引入 baseline 后能允许 review 前已有业务改动，同时拒绝 review 阶段新增或改变业务文件状态。

## 8. Follow-ups

- 设计 staged-only 或 path-limited local review 模式，帮助用户在工作区包含多组无关改动时聚焦 review。
- 将本地 review 的当前工作区 diff 语义补充到 README 或开发者文档中。
- 如果未来多个本地 agent workflow 都需要 dirty worktree baseline，可以抽象通用 baseline helper。
