# 产品规格：本地 review base 选择与 CI 保持一致

## 1. Summary

本需求优化 `review-pr-local` 和 `review-spec-local` 的本地快照生成行为，使本地生成的 `pr_diff.txt` 尽量使用与 CI PR review 相同的 base SHA。目标是减少因为本地 remote stale 或默认 base 顺序不合适导致的 diff 噪声，让本地 review 更接近 GitHub Actions 中真实 PR review 的输入。

期望结果是：当当前分支已有 GitHub PR 时，本地 review 优先使用该 PR 的真实 `baseRefOid` 作为 diff base；当当前分支没有可解析 PR 时，本地 fallback 默认 base 顺序优先 `origin/main`，再考虑 `upstream/main` 和本地 `main`。用户仍然可以通过 `--base` 显式覆盖 base。

## 2. Problem

当前 `.github/scripts/prepare_local_review_inputs.py` 的默认 base 顺序优先 `upstream/main`：

```text
upstream/main, origin/main, main
```

在本地 `upstream/main` 落后而 `origin/main` 更接近 PR 实际 base 的场景下，本地 `review-pr-local` 或 `review-spec-local` 会用过旧的 base 生成 `pr_diff.txt`。这样会把已经合入 `main` 的历史改动也纳入本地 review 快照，导致 review 输入明显大于 CI 输入，并让本地 review 产生不属于当前 PR 的噪声。

issue 115 的具体场景中，CI 使用 PR event 的真实 base SHA `b8dd9d9`，而本地默认选择了 stale 的 `upstream/main = b413a4d`，导致本地 `pr_diff.txt` 包含大量额外历史改动。

## 3. Goals

- 当前分支已有 GitHub PR 时，本地 review 生成 `pr_diff.txt` 应优先使用 PR 的真实 base SHA。
- 当前分支没有可解析 PR 时，默认 base 选择顺序应优先 `origin/main`，然后是 `upstream/main`，最后是本地 `main`。
- 用户通过 `--base` 显式传入 base 时，应继续使用用户指定值。
- `review-pr-local` 和 `review-spec-local` 应共同受益，因为它们都通过同一个本地快照脚本准备输入。
- 本地 `pr_description.txt` 中展示的 base 信息应与实际用于 diff 的 base 保持一致，避免描述和 diff base 不一致。
- 变更后本地 review 的 `pr_diff.txt` 应更接近 CI 的 `pr_diff.txt`，减少已经合入目标分支的历史改动噪声。
- 当 GitHub PR 信息无法获取、`gh` 不可用、当前分支没有 PR 或网络/API 失败时，本地 workflow 应继续可用，并走清晰的 fallback。

## 4. Non-goals

- 不改变 CI review workflow 的 base 选择；CI 已使用 PR event 中的真实 base/head SHA。
- 不改变 `review-pr-repo`、`review-spec-repo`、`review.json` 契约或评审标准。
- 不要求本地脚本自动 fetch 或同步 stale remote refs。
- 不改变 local review 对工作区 dirty changes、staged changes、untracked files 的快照语义。
- 不引入新的 GitHub API 写操作，不创建 PR、不发布评论、不修改远端状态。
- 不实现 feature；本 PR 仅创建规格。

## 5. Figma / design references

Figma: none provided。该需求是本地 CLI/workflow 行为变更，不涉及 UI 或视觉设计。

## 6. User experience

### 已有 PR 的本地 review

- 用户在已有 PR 的当前分支运行：

```bash
python3 .github/scripts/prepare_local_review_inputs.py \
  --expected-skill .agents/skills/review-pr-repo/SKILL.md
```

或通过 `review-pr-local` / `review-spec-local` skill 间接运行该脚本。

- 如果脚本能通过当前分支解析到 GitHub PR，则本地 diff base 使用该 PR 的 `baseRefOid`。
- 本地生成的 `pr_description.txt` 应显示该 PR 的 title、body、base ref、base SHA、head ref 和 head SHA。
- 本地生成的 `pr_diff.txt` 应基于 PR base SHA 与本地工作区快照生成，而不是基于 stale `upstream/main`。
- 输出给用户或 GitHub output 的 `base` / `base_sha` 应能反映实际使用的 base，便于排查。

### 没有 PR 或无法获取 PR 信息的 fallback

- 如果当前分支没有 PR、`gh pr view` 失败、GitHub CLI 不可用或返回数据无法解析，脚本继续使用本地 fallback。
- fallback 默认 base 顺序为：

```text
origin/main, upstream/main, main
```

- 如果 `origin/main` 存在，应优先使用 `origin/main`。
- 如果 `origin/main` 不存在但 `upstream/main` 存在，应使用 `upstream/main`。
- 如果两个 remote ref 都不存在但本地 `main` 存在，应使用 `main`。
- 如果都无法解析，应继续要求用户传入 `--base`，并给出清楚错误。

### 用户显式传入 `--base`

- 当用户传入 `--base <ref-or-sha>` 时，该值继续拥有最高优先级。
- 显式 `--base` 应用于 diff base，即使当前分支已有 PR。
- 本地 PR description fallback 中的 base 信息也应与显式 base 保持一致。

### 与 local review skills 的关系

- `review-pr-local` 和 `review-spec-local` 的使用方式不应改变。
- 用户不需要为常见已有 PR 分支额外传 `--base origin/main` 来规避 stale `upstream/main`。
- 纯 `specs/` diff 仍应选择 `review-spec-repo`；其他 diff 仍应选择 `review-pr-repo`。
- `spec_context.md` 生成规则不变：只有 code review skill 需要 spec context 时生成。

### 边界情况

- 当 PR base SHA 无法在本地 checkout 的对象库中解析时，脚本应失败并提示可操作原因，或保留现有失败行为；本需求不要求自动 fetch。
- 当 PR metadata 可获取但 PR base SHA 为空时，应走 fallback base，而不是用空 SHA 生成 diff。
- 当当前分支对应 closed PR、draft PR 或 PR 状态不是 open 时，local review 仍可以作为本地工具使用；本需求只关心已解析 PR 的 base 一致性，不新增 reviewable 状态 gate。
- 当 local worktree 没有可 review 的 diff 时，继续保持现有 “no local changes to review” 行为。

## 7. Success criteria

- 当前分支有 GitHub PR 且 `gh pr view` 返回 `baseRefOid` 时，脚本使用该 SHA 作为 `write_local_diff()` 的 base。
- 同一场景下，脚本不再先调用 `default_base()` 选择 `upstream/main` 作为 diff base。
- 当前分支没有可解析 PR 且未传 `--base` 时，`default_base()` 优先返回 `origin/main`。
- `upstream/main` 和 `origin/main` 都存在时，fallback 默认选择 `origin/main`。
- 用户传入 `--base upstream/main` 时，脚本使用 `upstream/main`，不被 PR metadata 覆盖。
- `review-pr-local` 和 `review-spec-local` 的命令示例无需改变即可获得新行为。
- 本地 `pr_description.txt` 的 base SHA 与实际用于生成 `pr_diff.txt` 的 base SHA 一致。
- 现有 dirty worktree snapshot 能力、skill 自动选择、`spec_context.md` 生成和 baseline status 逻辑不回退。

## 8. Validation

- 更新 `.github/scripts/prepare_local_review_inputs.py` 的单元测试，覆盖已有 PR 时优先使用 `baseRefOid` 生成 diff。
- 更新默认 base 顺序测试，覆盖 `origin/main` 优先于 `upstream/main`。
- 覆盖显式 `--base` 优先级，确认它不会被 PR metadata 覆盖。
- 覆盖 PR metadata 获取失败时继续使用 fallback base。
- 覆盖 PR metadata 中 base SHA 为空时不使用空 base。
- 运行 targeted tests：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_prepare_local_review_inputs
```

- 在实现触及 shared workflow 脚本时，建议运行完整测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

## 9. Open questions

- 是否要在未来增强为“当 `upstream/main` 和 `origin/main` 指向同一 repo 且 `upstream/main` 落后时自动选择较新的 ref”？本规格暂不要求，因为 PR base SHA 优先和 fallback 顺序调整已经覆盖主要问题。
- 当 PR base SHA 本地缺失时，是否应该自动 fetch base SHA？本规格暂不要求，以避免本地 review 脚本隐式执行网络和 remote 更新操作。
