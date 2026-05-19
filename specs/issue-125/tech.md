# Tech Spec: `update-dedupe` 自进化 dedupe 规则

## 1. Problem

需要新增一个 repo-local 自进化流程，从 GitHub 最近正式 duplicate 关闭记录中提取稳定 duplicate cluster，并把结果写入 `.agents/skills/dedupe-issue-repo/SKILL.md`。实现必须复用仓库现有 `update-pr-review` 的安全模式：runner 负责 GitHub 数据收集、临时输出、写入范围验证和 PR 发布；Codex skill 只负责把结构化证据转化为 concise guidance。

关键技术约束是不能修改 `.agents/skills/dedupe-issue/SKILL.md` 的核心合同，尤其不能改变 2-candidate minimum、similarity threshold、输出 schema 或 precision-over-recall 原则。

## 2. Relevant code

- `.agents/skills/dedupe-issue/SKILL.md` — core duplicate detection skill；已经定义可选 companion `.agents/skills/dedupe-issue-repo/SKILL.md` 的允许覆盖范围。
- `.agents/skills/update-pr-review/SKILL.md` — 可复用的 self-evolution skill 模式：读取聚合 JSON、写入 output directory、由 runner 应用。
- `.agents/skills/update-pr-review/scripts/aggregate_review_feedback.py` — GitHub GraphQL 聚合脚本模式，包含 repo 参数、时间窗口、pagination、JSON 输出。
- `.agents/skills/update-pr-review/scripts/apply_guidance_output.py` — 从 output directory 应用 proposed skill 文件的模式。
- `.agents/skills/update-pr-review/scripts/validate_write_surface.py` — 基于 changed paths 限制持久写入范围的模式。
- `.github/workflows/update-pr-review.yml` — self-evolution workflow 模板，包含 aggregation、Codex action、apply output、write-surface validation、change detection、固定分支 PR 创建。
- `.github/workflows/triage-issue.yml` — 当前 issue triage 调用 `triage-issue` 和 `dedupe-issue` 的入口；未来可通过 prompt 引用 companion guidance，但本功能不应改变 triage 输出合同。
- `.agents/skills/review-pr-repo/SKILL.md` 和 `.agents/skills/review-spec-repo/SKILL.md` — repo-local companion skill 的现有格式参考。

当前仓库已经存在 `.agents/skills/dedupe-issue-repo/SKILL.md` 初始 companion，包含 wrapper flow、边界和空的 `Known-duplicate clusters` 区域。因此实现应优先更新该 companion 的 known-cluster guidance；如果未来在其他分支或仓库中该文件不存在，apply 脚本仍应允许 runner 创建 parent directory 后写入完整 replacement。

## 3. Current state

`dedupe-issue` 当前只基于 workflow 提供的候选 issue 做保守相似度判断。它已经预留了 repo-specific companion 扩展点，但只有在 prompt 引用 companion 文件时才会读取，且 companion 只能影响 known-duplicate clusters 和 repo-specific normalization。

`update-pr-review` 已经建立了可复用模式：

- GitHub Actions 先用脚本聚合稳定人类反馈。
- Codex action 读取专用 skill，把 proposed replacement 写到临时 output directory。
- apply 脚本验证 output contract 并复制到允许路径。
- write-surface guard 检查 git changed paths 只落在允许目录。
- 有变化才在固定分支上提交并创建或更新 PR。

本功能应复制这种模式，但输入数据从 PR review feedback 变为 issue duplicate timeline evidence，目标 companion 从 review companion skills 变为 dedupe companion skill。

## 4. Proposed changes

### 新增 skill

新增 `.agents/skills/update-dedupe/SKILL.md`，职责边界与 `update-pr-review` 类似：

- 读取 runner 提供的 aggregated duplicate feedback JSON。
- 只基于强证据识别 repeated duplicate clusters。
- 把 cluster 转换为 `.agents/skills/dedupe-issue-repo/SKILL.md` 中 `Known-duplicate clusters` 的 concise guidance。
- 写入 `update-dedupe-output/status.json`。
- 当 `status == "changed"` 时，写入完整 replacement file：`update-dedupe-output/dedupe-issue-repo/SKILL.md`。
- 不直接编辑 `.agents`、不运行 git、不调用 GitHub API、不创建 PR。

建议 output contract：

```json
{
  "status": "changed",
  "reason": "Brief evidence summary.",
  "updated_files": [".agents/skills/dedupe-issue-repo/SKILL.md"]
}
```

允许状态：

- `changed`：有足够证据且 guidance 需要更新。
- `no_change`：证据不足、重复模式已覆盖，或没有维护者强信号。
- `error`：输入无法安全解释或缺少必要字段。

### Companion skill

使用现有 `.agents/skills/dedupe-issue-repo/SKILL.md` 作为 `dedupe-issue` 的 repo-specific wrapper。`update-dedupe` 只应维护该文件中的 known-cluster guidance，并保留以下结构：

- frontmatter：`name: dedupe-issue-repo`、`specializes: dedupe-issue`。
- Required Wrapper Flow：读取 `.agents/skills/dedupe-issue/SKILL.md`，遵守核心流程，再应用 repo-specific guidance。
- Boundaries：明确 companion 不能改变 duplicate algorithm、2-candidate minimum、similarity threshold、output contract 或 safety rules。
- Known-duplicate clusters：由 `update-dedupe` 维护的简短规则列表。
- Self-Evolution Boundary：说明 `update-dedupe` 可以更新该文件，但只能依据 repeated maintainer duplicate evidence。

第一版不需要在没有 repeated cluster 时改写 companion；无证据时 runtime skill 应输出 `no_change`。

### 聚合脚本

新增 `.agents/skills/update-dedupe/scripts/aggregate_dedupe_feedback.py`。建议命令行参数：

- `--repo owner/name`，默认通过 `gh repo view --json nameWithOwner` 推导。
- `--days N`，默认 7。
- `--issue NUMBER`，可选；用于调试或回放单个 issue。
- `--output PATH`，可选；未提供时写入带时间戳的 temp JSON 并打印路径。

数据收集建议使用 `gh api graphql`，因为需要 issue 状态、关闭原因和 timeline events。核心查询应获取：

- issue number、title、url、state、stateReason、closedAt、author。
- timeline 中的 `MarkedAsDuplicateEvent` 或 GitHub GraphQL 对应类型。
- canonical issue number、title、url、repository 信息。
- actor、createdAt 等 evidence metadata。

分页必须处理 issue 列表和 timeline connection。脚本应把 GitHub API 字段归一化为稳定 JSON，避免让 skill 直接理解复杂 GraphQL shape。

建议输出 shape：

```json
{
  "generated_at": "2026-05-19T00:00:00+00:00",
  "repo": "owner/name",
  "days": 7,
  "issues": [
    {
      "number": 123,
      "title": "example duplicate",
      "url": "https://github.com/owner/repo/issues/123",
      "state_reason": "duplicate",
      "closed_at": "2026-05-19T00:00:00Z",
      "canonical": {
        "number": 45,
        "title": "canonical issue",
        "url": "https://github.com/owner/repo/issues/45"
      },
      "evidence": {
        "event_type": "marked_as_duplicate",
        "actor": "maintainer-login",
        "created_at": "2026-05-19T00:00:00Z"
      }
    }
  ],
  "clusters": [
    {
      "canonical": {
        "number": 45,
        "title": "canonical issue",
        "url": "https://github.com/owner/repo/issues/45"
      },
      "duplicates": [
        {
          "number": 123,
          "title": "example duplicate",
          "url": "https://github.com/owner/repo/issues/123"
        }
      ]
    }
  ]
}
```

脚本可以只输出 raw `issues`，由 skill 聚合 clusters；但让脚本同时输出 deterministic `clusters` 会减少 prompt ambiguity，并便于测试。

过滤规则：

- 只纳入 `state_reason == "duplicate"` 的 closed issue。
- 缺少 canonical duplicate event 的 issue 不纳入 `clusters`；可选地放入 `skipped` 供审计。
- 同一个 duplicate issue 不应重复计数。
- canonical issue 可以是 open 或 closed，但必须能解析为 issue。

### Apply 脚本

新增 `.agents/skills/update-dedupe/scripts/apply_guidance_output.py`，可从 `update-pr-review` 版本改造：

- `ALLOWED_FILES` 只允许 `.agents/skills/dedupe-issue-repo/SKILL.md`。
- source path 为 `dedupe-issue-repo/SKILL.md`。
- 校验 `status`、`reason`、`updated_files`。
- `no_change` 时只打印原因并退出 0。
- `error` 时退出非 0，阻止 runner 继续发布。
- `changed` 时复制完整 proposed file 到目标路径，必要时创建 parent directory。

### Write-surface guard

新增 `.agents/skills/update-dedupe/scripts/validate_write_surface.py`，可从 `update-pr-review` 改造：

- `ALLOWED_PREFIXES = (".agents/skills/dedupe-issue-repo/",)`。
- 检查 tracked diff 和 untracked files。
- 任何不在允许前缀内的 path 都应失败。

注意：workflow 自身新增脚本和 skill 是实现 PR 的一部分；运行时 guard 用于自进化 PR 生成阶段。实现该 feature 的 PR 需要测试 guard 的 path 参数模式，避免它在开发分支上误判实现文件本身。

### GitHub Actions workflow

新增 `.github/workflows/update-dedupe.yml`，参考 `update-pr-review.yml`：

- `workflow_dispatch` inputs：
  - `days`，默认 `"7"`。
  - `issue`，可选单 issue 调试。
  - `repo`，可选，默认 `${{ github.repository }}`。
- permissions：
  - `contents: write`
  - `pull-requests: write`
  - `issues: read`
- concurrency group：`update-dedupe`。
- steps：
  1. checkout default branch。
  2. 运行 `aggregate_dedupe_feedback.py --repo ... --days ... --output dedupe-feedback.json`。
  3. 安装 Codex sandbox prerequisites。
  4. 配置 Codex API endpoint。
  5. 准备 `update-dedupe-output/`。
  6. Codex action 读取 `.agents/skills/update-dedupe/SKILL.md` 和 `dedupe-feedback.json`，只写 `update-dedupe-output/`。
  7. 运行 `apply_guidance_output.py`。
  8. 删除临时 JSON 和 output directory。
  9. 运行 `validate_write_surface.py`。
  10. 检查 `.agents/skills/dedupe-issue-repo` 是否有 diff。
  11. 有 diff 时切到固定分支 `feat/update-dedupe`，提交 `docs(skill): update dedupe guidance`，push，并 create/edit PR。

workflow prompt 应明确：

- 不编辑 `.agents` 直接输出。
- 只从 strong duplicate evidence 学习。
- 不修改 core `dedupe-issue`。
- 不运行 git、commit、push、create PR 或调用 GitHub APIs。

### Triage workflow integration

本 issue 的核心是新增 update 流程，不要求立即改动 `triage-issue.yml`。不过为了让未来 companion 生效，应确认现有 triage prompt 能引用 optional companion skill paths。当前 workflow 已有：

```text
If the prompt or triage_context.json references optional companion
skill paths that exist, read them only as repository-specific
guidance under the limits defined by the core skills.
```

如果 `prepare_issue_triage_context.py` 已经会提供 companion reference，则无需改动。若没有，后续实现可在不改变输出 schema 的前提下，让 triage prompt 或 context 明确引用 `.agents/skills/dedupe-issue-repo/SKILL.md`。这项集成应保持很小，并且不得改变 duplicate candidate list 的权威来源。

## 5. End-to-end flow

1. 维护者手动触发 `Update Dedupe Guidance` workflow。
2. workflow checkout default branch，并运行聚合脚本。
3. 聚合脚本通过 `gh` 查询最近 N 天关闭为 duplicate 的 issue。
4. 脚本过滤掉没有 canonical duplicate event 的记录，生成 `dedupe-feedback.json`。
5. Codex action 读取 `update-dedupe` skill 和 JSON 输入。
6. skill 识别 repeated clusters：
   - cluster duplicate count >= 2 时可生成或更新 guidance。
   - count < 2 且没有明确维护者统一规则时输出 `no_change`。
7. skill 写入 `update-dedupe-output/status.json`，必要时写入完整 proposed `dedupe-issue-repo/SKILL.md`。
8. runner 应用 output，删除临时文件，并验证持久改动只在 `.agents/skills/dedupe-issue-repo/`。
9. 有 diff 时，runner 在 `feat/update-dedupe` 分支创建或更新 PR。
10. 之后 issue triage 运行时，如果 prompt/context 引用 companion，`dedupe-issue` 在核心合同内使用 known clusters 作为 repo-specific guidance。

## 6. Risks and mitigations

- 风险：GitHub GraphQL duplicate timeline 字段名称或可用性与预期不同。
  - 缓解：将 GraphQL 查询和 normalization 封装在聚合脚本中；为 missing canonical event 提供 `skipped` 或清晰错误；用 fixture 测试。
- 风险：从弱信号学习导致错误 duplicate guidance。
  - 缓解：严格要求 `state_reason == "duplicate"` 和 canonical event；普通评论不作为证据；小于两个独立 duplicate 不更新。
- 风险：self-evolution 修改核心 skill，破坏 dedupe 合同。
  - 缓解：apply 脚本和 write-surface guard 只允许 `.agents/skills/dedupe-issue-repo/`。
- 风险：generated guidance 过长或过度拟合个案。
  - 缓解：`update-dedupe` skill 明确要求 concise guidance，只记录 canonical 和关键识别信号。
- 风险：首次创建 companion 后 triage 未读取它。
  - 缓解：实现时验证 triage prompt/context companion reference；必要时增加最小集成测试或文档说明。
- 风险：fixed branch PR 覆盖未合并人工修改。
  - 缓解：沿用 `update-pr-review` 的 `git fetch`、`git switch -C`、`push --force-with-lease` 模式；PR 内容保持单一 allowed path。
- 风险：workflow 的 runtime write-surface guard 在开发实现 PR 中误判新增 workflow/scripts。
  - 缓解：guard 只在 workflow 自我更新阶段运行；单元测试使用 `--path` 参数验证允许和拒绝路径。

## 7. Testing and validation

- `aggregate_dedupe_feedback.py` 单元测试或 fixture 测试：
  - 默认参数和 `--repo` parsing。
  - `state_reason != "duplicate"` 被忽略。
  - 缺少 `marked_as_duplicate` canonical event 被忽略或进入 skipped。
  - 两个 duplicate issue 指向同一 canonical 时输出 cluster。
  - pagination 合并不会重复计数。
- `apply_guidance_output.py` 测试：
  - missing `status.json` 失败。
  - invalid JSON 失败。
  - invalid status 失败。
  - `no_change` 退出 0 且不要求 proposed file。
  - `changed` 只接受 `.agents/skills/dedupe-issue-repo/SKILL.md`。
  - source file 缺失时失败。
  - parent directory 不存在时能创建。
- `validate_write_surface.py` 测试：
  - `.agents/skills/dedupe-issue-repo/SKILL.md` 通过。
  - `.agents/skills/dedupe-issue/SKILL.md` 失败。
  - `.github/workflows/update-dedupe.yml`、README、production code、tests 路径失败。
- skill 内容 review：
  - `update-dedupe` 明确禁止直接编辑 `.agents` 和调用 GitHub API。
  - `dedupe-issue-repo` 明确继承并尊重核心 `dedupe-issue`。
- workflow dry run 或手动审查：
  - 无变化时不创建 PR。
  - 有变化时只提交 `.agents/skills/dedupe-issue-repo/SKILL.md`。
  - PR body 包含 evidence summary 和非关闭 issue reference。

## 8. Follow-ups

- 如果维护者需要从“明确评论指令”学习规则，应先定义可信来源和结构化格式，再扩展聚合脚本；第一版建议只依赖正式 duplicate timeline。
- 可以在后续 issue 中增强 `prepare_issue_triage_context.py`，显式注入 `.agents/skills/dedupe-issue-repo/SKILL.md` companion reference，前提是不改变 `dedupe-issue` 输出合同。
- 可以增加一个小型 markdown normalization helper，帮助 generated guidance 避免重复 cluster 或过长 bullet，但不应阻塞第一版。
