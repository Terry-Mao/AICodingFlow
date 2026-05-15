# 技术规格：实现 PR review verdict 发布与 reviewer request

## 1. Problem

当前 PR review 自动化已经能生成 `review.json` 并通过 `.github/scripts/post_pr_review.py` 发布到 GitHub，但发布脚本固定使用 `event: "COMMENT"`。同时 `.agents/skills/review-pr/scripts/validate_review_json.py` 只允许 `body` 和 `comments` 两个顶层字段，`review-pr` / `review-spec` skill 也按该旧契约输出。

要实现 issue 51，需要把 review 输出契约、validator、发布脚本和测试一起更新，使 `verdict` 成为稳定字段，并让发布脚本根据 PR 作者身份、PR 类型和 `verdict` 决定 GitHub review event 与可选 reviewer request。

## 2. Relevant code

- `.github/workflows/review-pr.yml` — PR review workflow，生成 `pr_description.txt`、`pr_diff.txt`，选择 review skill，运行 Codex，校验 `review.json`，再调用 `post_pr_review.py` 发布。
- `.github/scripts/select_review_skill.py` — 已有 `is_spec_only(files)` 逻辑，可作为 spec-only 判定规则参考。
- `.github/scripts/post_pr_review.py` — 当前固定构造 `{"event": "COMMENT", ...}` 并调用 GitHub create review API；需要在这里加入 event 选择、PR author 判断、CODEOWNERS 读取和 reviewer request。
- `.agents/skills/review-pr/scripts/validate_review_json.py` — 当前拒绝 `verdict` 和 `recommended_reviewers` 等未知顶层字段；需要扩展 schema 校验。
- `.agents/skills/review-pr/SKILL.md` — 当前 `review.json` 输出 shape 只包含 `body` 和 `comments`；需要要求 code review 输出 `verdict`，并说明 `recommended_reviewers` 使用边界。
- `.agents/skills/review-spec/SKILL.md` — 当前 spec review 输出 shape 只包含 `body` 和 `comments`，并明确“不添加 `verdict`”；需要同步新契约。
- `tests/test_post_pr_review.py` — 已覆盖 diff position 映射、comment normalization 和固定 `COMMENT` 发布；需要扩展 event matrix 与 reviewer request 测试。
- `tests/test_validate_review_json.py` — 当前只有基础类型校验测试；需要覆盖新顶层字段。
- `.github/CODEOWNERS` — reviewer 来源。实现应能处理文件不存在或无合格 owner 的情况。

## 3. Current state

现有 end-to-end 流程：

1. `review-pr.yml` 生成稳定 PR 快照。
2. `select_review_skill.py` 根据 changed files 选择 `review-pr-repo` 或 `review-spec-repo`。
3. Codex 按 skill 写出 `review.json`。
4. `validate_review_json.py` 校验 `review.json`。
5. `post_pr_review.py` 发布 GitHub PR review。

当前限制：

- `review.json` 不能包含 `verdict`。
- `review.json` 不能包含 `recommended_reviewers`。
- 发布脚本没有读取 `pull_request.author_association`。
- 发布脚本没有区分 spec-only PR 和 code PR。
- 发布脚本不读取 `.github/CODEOWNERS`。
- 发布脚本不调用 reviewer request API。
- 所有 Bot 评审最终都是 GitHub `COMMENT`。

## 4. Proposed changes

### 扩展 `review.json` schema

更新 `.agents/skills/review-pr/scripts/validate_review_json.py`：

- 允许顶层字段：`verdict`、`body`、`comments`、可选 `recommended_reviewers`。
- 要求 `verdict` 必填且类型为 string。
- `verdict` 只允许 `"APPROVE"` 或 `"REJECT"`。
- `body` 仍为 string。
- `comments` 仍为 list，并继续复用现有 inline target、severity、suggestion 校验。
- `recommended_reviewers` 如果存在，必须是 list。
- `recommended_reviewers` 中每个元素必须是 string。
- `recommended_reviewers` 长度不得超过 1。
- validator 只做结构校验，不负责判断 reviewer 是否出现在 `.github/CODEOWNERS`，因为它当前只接收 `pr_diff.txt` 和 `review.json`。

### 更新 review skills 输出契约

更新 `.agents/skills/review-pr/SKILL.md` 和 `.agents/skills/review-spec/SKILL.md`：

- 输出示例改为包含 `verdict`。
- 说明 `APPROVE` 表示没有阻塞级发现。
- 说明 `REJECT` 表示存在需要修复后再合并的阻塞级发现。
- 说明 `recommended_reviewers` 是可选字段，只有当调用工作流需要 human reviewer recommendation 时才返回。
- 删除或改写 `review-spec` 中“不添加 `verdict`”的旧约束。
- 保留既有 `body`、`comments`、inline target、severity labels 和 suggestion 规则。

### 在发布脚本中选择 GitHub review event

在 `.github/scripts/post_pr_review.py` 中新增小函数，保持逻辑可单元测试：

- `changed_files_from_diff(path: Path) -> list[str]`
- `is_spec_only(files: list[str]) -> bool`
- `is_bot_author(pr: dict[str, Any]) -> bool`
- `is_non_member_author(pr: dict[str, Any]) -> bool`
- `is_non_member_code_review_subject(pr: dict[str, Any], files: list[str]) -> bool`
- `review_event_for(pr: dict[str, Any], files: list[str], verdict: str) -> str`

建议规则：

```text
ORG_MEMBER_ASSOCIATIONS = {"COLLABORATOR", "MEMBER", "OWNER"}

if not is_non_member_code_review_subject(pr, files):
    return "COMMENT"
if verdict == "REJECT":
    return "REQUEST_CHANGES"
return "COMMENT"
```

`is_non_member_code_review_subject` must return `False` for spec-only PRs. This
keeps `review-spec` verdicts machine-readable while preventing spec-only PRs
from using the non-member `REQUEST_CHANGES` or human reviewer request flow.

`is_non_member_author` 细节：

- 从 `pr.get("author_association")` 读取身份。
- 如果 author association 不是非空 string，返回 `False`。
- 如果值在 `ORG_MEMBER_ASSOCIATIONS`，返回 `False`。
- 如果 `is_bot_author(pr)` 为真，返回 `False`。
- 其他情况返回 `True`。

`is_bot_author` 可优先使用 GitHub event 中的 `pull_request.user.type == "Bot"`。为了兼容 automation user，也可把 login 以 `[bot]` 结尾视为 bot。

### 请求 human reviewer

在 `.github/scripts/post_pr_review.py` 中实现 reviewer request helper：

- `parse_codeowners(path: Path) -> list[CodeownersRule]`
- `codeowners_candidates_for_file(rules, changed_path) -> list[str]`
- `eligible_owner(owner: str, pr_author_login: str, all_codeowners: set[str]) -> bool`
- `select_reviewer(review: dict[str, Any], rules, changed_files, pr_author_login) -> str | None`
- `request_reviewer(repo: str, token: str, pr_number: int, reviewer: str) -> None`

推荐实现边界：

- CODEOWNERS parser 只需要支持本仓库当前需要的常见格式：空行、`#` 注释、pattern 后跟一个或多个 owners。
- Owner token 保留 GitHub 写法中的 `@` 可读性，但调用 reviewer request API 时去掉开头 `@`。
- 先校验 `review["recommended_reviewers"]`：
  - 长度必须为 1。
  - reviewer 不能等于 PR author login。
  - reviewer 必须出现在 CODEOWNERS owners 集合。
- 如果 recommended reviewer 不合格，进入 fallback。
- Fallback 按 changed files 顺序查找最后匹配的 CODEOWNERS rule，并取该 rule 中第一个合格 owner。
- 如果所有 changed files 都没有合格匹配，取 CODEOWNERS 文件中第一个合格 owner。
- 没有合格 reviewer 时返回 `None`，发布脚本打印说明并跳过 reviewer request。

Reviewer request API：

```text
POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers
{
  "reviewers": ["Terry-Mao"]
}
```

如果后续需要支持 team owner，应另行加入 `team_reviewers`，本次不作为必须范围。

### 发布顺序

`post_pr_review.py` 的主流程建议为：

1. 读取 event、PR、review、diff。
2. 规范化 inline comments。
3. 根据 `verdict`、PR 作者身份和 changed files 选择 GitHub review event。
4. 发布 PR review。
5. 如果满足 `non-member code PR + verdict = APPROVE`，尝试选择并请求 1 个 CODEOWNERS reviewer。Spec-only PR 即使作者是 non-member，也不进入该分支。

发布 review 应先于 reviewer request。这样即使 CODEOWNERS 缺失或 reviewer request 失败，已有 Bot review 仍能留下主要反馈。对 reviewer request 的 GitHub API 错误建议记录并继续，除非错误表示认证或权限完全不可用且仓库希望 fail fast；本规格建议不让 reviewer request 失败阻断 review 发布。

### Workflow 变更

`.github/workflows/review-pr.yml` 已经传入 `review.json` 和默认 `pr_diff.txt`，并提供 `GITHUB_TOKEN`。本功能原则上不需要新增 workflow step。

需要确认：

- `post_pr_review.py` 在当前 checkout 下可以读取 `.github/CODEOWNERS`。
- `pull-requests: write` 权限足以发布 review 和请求 reviewer。

## 5. End-to-end flow

1. PR 触发 `review-pr.yml`。
2. Workflow 生成 `pr_description.txt` 和 `pr_diff.txt`。
3. Workflow 选择 `review-pr-repo` 或 `review-spec-repo`。
4. Codex 输出包含 `verdict` 的 `review.json`。
5. `validate_review_json.py pr_diff.txt review.json` 校验通过。
6. `post_pr_review.py` 读取 GitHub event 中的 `pull_request`。
7. 脚本从 `pr_diff.txt` 提取 changed files，并判断是否 spec-only。
8. 脚本根据 PR author、PR 类型和 `verdict` 选择 `COMMENT` 或 `REQUEST_CHANGES`。
9. 脚本调用 create review API 发布 review。
10. 如果是 `non-member code PR + APPROVE`，脚本读取 `.github/CODEOWNERS`，校验或 fallback reviewer，并调用 requested reviewers API。

## 6. Risks and mitigations

- 风险：旧版 agent 仍输出没有 `verdict` 的 `review.json`。
  - 缓解：validator 失败并阻止发布；同时更新 `review-pr` 和 `review-spec` skill，确保 Codex 生成新契约。
- 风险：把 member PR 的 `REJECT` 发布成 blocking review 影响维护者迭代。
  - 缓解：event mapping 明确 member / collaborator / owner 始终使用 `COMMENT`。
- 风险：`author_association` 缺失时误判外部贡献者并错误 request changes。
  - 缓解：缺失或异常时返回非 non-member，使用 `COMMENT`。
- 风险：bot PR 被当作 non-member。
  - 缓解：检测 `pull_request.user.type == "Bot"` 和 `[bot]` login。
- 风险：CODEOWNERS parser 与 GitHub 完整匹配语义不完全一致。
  - 缓解：先支持本仓库使用的简单规则；复杂 CODEOWNERS pattern 或 team owner 作为后续增强。
- 风险：`REQUEST_CHANGES` 阻塞由 branch protection 决定，用户误解 `verdict` 就是 merge gate。
  - 缓解：skill 文档和 README 如有更新，应说明 `verdict`、review event 和 branch protection 的区别。
- 风险：spec-only PR 的 `REJECT` 没有 blocking event，文档问题可能仍可合并。
  - 缓解：这是本 issue 指定行为；`review-spec` 的 `verdict` 用于机器可读地表达文档评审结论，并保证 body 中的 “Approve / Request changes” 与结构化结果一致。spec-only PR 继续依赖维护者 review、required checks 和 branch protection。

## 7. Testing and validation

更新 `tests/test_validate_review_json.py`：

- 接受包含 `verdict: "APPROVE"`、`body`、`comments` 的最小合法 review。
- 接受 `verdict: "REJECT"`。
- 拒绝缺失 `verdict`。
- 拒绝未知 `verdict`。
- 接受空 `recommended_reviewers` 或 1 个字符串 reviewer。
- 拒绝多个 `recommended_reviewers`。
- 拒绝非字符串 reviewer。
- 保留现有 inline comment target、severity 和 suggestion 校验覆盖。

更新 `tests/test_post_pr_review.py`：

- member code PR + `APPROVE` 发布 `COMMENT`。
- member code PR + `REJECT` 发布 `COMMENT`。
- non-member code PR + `REJECT` 发布 `REQUEST_CHANGES`。
- non-member code PR + `APPROVE` 发布 `COMMENT` 并请求 reviewer。
- non-member spec-only PR + `REJECT` 发布 `COMMENT` 且不请求 reviewer。
- bot author + `REJECT` 发布 `COMMENT`。
- 缺失 `author_association` + `REJECT` 发布 `COMMENT`。
- recommended reviewer 合法时优先使用。
- recommended reviewer 是 PR author 或不是 CODEOWNERS owner 时 fallback。
- CODEOWNERS 缺失或没有合格 owner 时不请求 reviewer，但 review 发布仍完成。

可选人工验证：

```bash
python3 -m unittest tests.test_validate_review_json tests.test_post_pr_review
python3 -m unittest discover -s tests
```

## 8. Follow-ups

- 后续可支持 CODEOWNERS team owner，并通过 `team_reviewers` 请求团队 review。
- 后续可在 README 中补充 `verdict`、GitHub review event、branch protection 的关系说明。
- 后续可增加集成 fixture，覆盖完整 `pr_diff.txt` + `review.json` + GitHub event payload 的发布路径。
