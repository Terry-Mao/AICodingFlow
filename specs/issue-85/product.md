# 产品规格：允许本地 review 在有工作区改动时运行

## 1. Summary

`review-pr-local` 和 `review-spec-local` 是开发者在本地提交前运行 AI review 的入口。当前本地 review 准备阶段要求整个 Git working tree 必须干净，否则直接中止。这和 issue 中描述的常见开发流程冲突：开发者通常希望先完成本地修改、运行 review、根据 review 调整，再把最终结果整理成 commit。

本功能要求本地 review 支持在工作区存在未提交修改时运行，并基于当前工作区内容生成 review 输入。目标是让本地 review 成为提交前的质量检查步骤，而不是只能在提交后运行的检查。

## 2. Problem

当前流程要求开发者先 commit，再运行 `review-pr-local` 或 `review-spec-local`。如果 review 发现问题，开发者需要继续修改并产生额外修正 commit，或者后续再 squash / amend。对于偏好“review 完再 commit”的开发习惯，这会增加提交历史整理成本，也让本地 review 的使用时机不自然。

该限制还会让本地 review 与 CI review 的定位混淆：CI review 可以基于已提交 PR diff 运行，而本地 review 更适合作为提交前对当前工作区的快速自查。

## 3. Goals

- `review-pr-local` 和 `review-spec-local` 在工作区存在未提交修改时仍能准备并运行 review。
- 本地 review 生成的 `pr_diff.txt` 必须反映当前工作区相对选定 base 的实际待 review 内容，而不只包含 `HEAD` 已提交内容。
- 本地 review 仍然只允许产出受控的根目录临时文件：`pr_description.txt`、`pr_diff.txt`、`spec_context.md`、`review.json`，以及用于 dirty worktree 校验的 `.local_review_baseline.status`。
- 本地 review 不应自动 stage、commit、stash、push 或修改用户的业务文件。
- 如果工作区没有实际待 review 的 diff，流程应给出清晰失败或跳过原因，而不是生成误导性的空 review。
- 保留现有按 diff 自动选择 `review-pr-repo` 或 `review-spec-repo` 的行为。

## 4. Non-goals

- 不实现功能或修改生产代码；本 PR 仅创建规格。
- 不改变 CI 上的 PR review workflow 行为。
- 不改变 `review-pr-repo`、`review-spec-repo`、`review-pr` 或 `review-spec` 的评审标准。
- 不要求本地 review 自动创建临时 commit、stash 或分支。
- 不要求解决已 staged 与 unstaged 改动的拆分 review；本功能只要求当前工作区整体可被 review。
- 不要求 review 结束后自动清理 `review.json` 或其他快照文件。

## 5. Figma / design references

Figma: none provided。该需求是本地命令与 agent skill 工作流行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### 默认本地工作流

- 开发者在本地完成一组修改，但尚未 commit。
- 开发者运行 `review-pr-local` 或 `review-spec-local` skill。
- skill 的准备步骤不再因为业务文件有未提交改动而中止。
- 准备步骤生成或刷新根目录快照文件：
  - `pr_description.txt`
  - `pr_diff.txt`
  - `spec_context.md`，仅在代码 review 需要 spec context 时存在
  - `.local_review_baseline.status`，用于记录 review 前的工作区状态并在校验阶段使用
  - 后续 review 阶段生成 `review.json`
- review 内容应覆盖开发者当前准备提交的改动，包括已 staged 和 unstaged 的 tracked file 修改，以及需要纳入 review 的新文件。
- review 完成后，开发者可以继续修改、重新运行 review，最后再自行 commit。

### 工作区状态规则

- 干净工作区仍然可运行本地 review，行为保持兼容。
- 有未提交业务文件改动时，本地 review 必须可运行。
- 已 staged 的业务文件改动不应被拒绝；它们属于当前工作区待 review 内容。
- 未 staged 的业务文件改动不应被拒绝；它们也属于当前工作区待 review 内容。
- 新增但未跟踪的业务文件如果位于通常会进入 Git diff 的项目路径中，应纳入 review diff，避免新文件漏审。
- 根目录旧的 review 快照文件可以像当前行为一样在准备阶段被清理或覆盖。
- `.local_review_baseline.status` 可以在下次准备阶段被覆盖，不需要单独清理脚本，且不应被纳入提交。
- 本地 review 过程中如果产生除允许快照以外的新改动，仍应被 `validate_local_review_result.py` 拒绝。

### Diff 语义

- `pr_diff.txt` 应表示“当前工作区相对 base 的完整待 review 变化”。
- 当工作区有未提交修改时，`pr_diff.txt` 不应只使用 `base...HEAD` 的 committed diff，因为那会漏掉用户正在 review 的改动。
- 当工作区没有未提交修改时，`pr_diff.txt` 可以继续表示 `base...HEAD` 的 committed diff。
- 如果同时存在 `HEAD` 之后的提交和未提交修改，review 应覆盖两者合并后的当前文件状态与 base 的差异。
- 本地 review 不应把临时 review 输出文件自身纳入 `pr_diff.txt`。
- 本地 review 不应把 `.local_review_baseline.status` 纳入 `pr_diff.txt`。

### 错误与跳过体验

- 如果无法解析 base、repo 或 head，保留现有错误语义。
- 如果相对 base 没有任何可 review diff，应清晰提示没有本地改动或提交可 review。
- 如果 diff 只包含被忽略或不应 review 的临时快照文件，不应产生有效 review。
- 如果运行过程中发现 review 阶段修改了业务文件，应继续失败并指出不允许的文件路径。

## 7. Success criteria

- 在存在 unstaged tracked file 修改时运行 `review-pr-local`，流程可以生成 `pr_diff.txt` 并继续进入 review。
- 在存在 staged tracked file 修改时运行 `review-pr-local`，流程可以生成 `pr_diff.txt` 并继续进入 review。
- 在存在新增未跟踪文件时运行本地 review，`pr_diff.txt` 包含该新文件的内容或等价可 review diff。
- 在同时存在 committed changes 和 uncommitted changes 时，`pr_diff.txt` 覆盖当前工作区相对 base 的完整变化。
- `review-spec-local` 对纯 `specs/` 变化仍选择 `review-spec-repo`。
- `review-pr-local` 对非纯 `specs/` 变化仍选择 `review-pr-repo`，并在需要时生成 `spec_context.md`。
- 旧的根目录快照文件在准备阶段仍会被清理或覆盖，且不会被纳入待 review diff。
- `.local_review_baseline.status` 被 `.gitignore` 忽略、可覆盖，且不会被纳入待 review diff。
- 本地 review 阶段仍只能新增或修改允许的 review 输出文件；业务文件被 review 阶段修改时校验失败。
- 本地 review 不执行 `git add`、`git commit`、`git stash`、`git push` 或 GitHub API 发布操作。

## 8. Validation

- 增加或更新 `prepare_local_review_inputs` 的单元测试，覆盖 dirty worktree 不再被准备阶段拒绝。
- 增加 diff 生成测试，覆盖 committed-only、unstaged、staged、untracked 以及 mixed 状态。
- 增加测试确认根目录 review 快照文件不会进入 `pr_diff.txt`。
- 增加测试确认 `.local_review_baseline.status` 被忽略且不会进入 `pr_diff.txt`。
- 保留并扩展 selected skill 测试，确认当前工作区 diff 仍驱动 `review-pr-repo` / `review-spec-repo` 选择。
- 保留 `validate_local_review_result.py` 测试，确认 review 阶段仍不能改动业务文件或 staged 输出。
- 手动验证可运行 `review-pr-local` 和 `review-spec-local`，分别在有未提交代码改动和纯 spec 改动时完成本地 review。

## 9. Open questions

- 未跟踪文件是否应完全按 Git 的 ignore 规则过滤，还是只纳入非 ignored 文件？本规格假设只纳入 Git 会认为可跟踪、未被 ignore 的文件。
- 如果用户只想 review staged changes 而不是整个工作区，是否需要新增参数？本规格暂不支持，避免扩大范围。
- 如果工作区包含与当前任务无关的本地改动，是否需要交互式选择文件？本规格暂不支持，由用户自行管理工作区范围。
