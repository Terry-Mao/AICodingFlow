# GitHub 协作流

GitHub 协作流把 issue、labels、assignees、PR review 和 comments 串成可自动化的流程：

```text
issue -> triage/spec -> implement -> pr -> review -> comments -> merge
```

核心原则是：workflow 负责稳定上下文、校验输出和执行 GitHub 写操作；Codex 只读取本地快照文件，产出结构化结果和工作区 diff。

## 环境变量和权限

| 名称 | 类型 | 用途 |
| --- | --- | --- |
| `CODEX_API_KEY` | Actions secret | Codex action 使用的模型服务 API key。 |
| `CODEX_API_ENDPOINT` | Actions variable | Responses API endpoint，可以是 base URL 或 `/responses` URL。 |
| `CODEX_MODEL` | Actions variable | Codex 使用的模型名称；为空时使用 Codex 默认模型。 |
| `AGENT_LOGIN` | Actions variable | issue / PR comment 中被分配或 mention 的 agent 登录名。 |
| `REVIEW_BOT_LOGIN` | Actions variable | 可选。发布 PR review 的 bot 登录名；默认 `github-actions[bot]`。如果 `review-pr.yml` 改用其他 token / bot 账号发 review，需要设置为实际 review 作者。 |
| `APP_ID` | Actions variable | GitHub App ID；需要提交 workflow 文件更新时使用。 |
| `APP_PRIVATE_KEY` | Actions secret | GitHub App private key；App 需要 `Contents: Read and write` 和 `Workflows: Read and write`。 |

目标仓库已有自己的 CI 时，不要在 CI 成功路径中再次 dispatch `review-pr.yml`。自动审查由该 workflow 的 `pull_request_target` 入口直接触发；CI 保持自己的测试编排。若需要测试通过后才审查，应先关闭直接触发入口，再设计单独的 CI 分发路径，避免两个入口同时运行。
使用 `GITHUB_TOKEN` 创建或更新 PR 的工作流在 PR 操作完成后显式 dispatch `review-pr.yml`；默认跳过 draft PR。implementation 工作流新建 PR 时，即使之前使用 GitHub App token 推送 workflow 文件，也显式分发并允许审查新建的 draft PR。仅更新已有 PR 且使用 App token 推送时，依靠推送产生的 `pull_request_target` 事件，跳过显式分发。常规 PR 仍由 `pull_request_target` 触发。

所有 Codex workflow 使用同一组模型配置。`CODEX_API_KEY` 和 `CODEX_API_ENDPOINT` 必须配置；`CODEX_MODEL` 可选，为空时使用 Codex 默认模型。`CODEX_API_ENDPOINT` 必须提供 Responses API；仅提供 Chat Completions 的模型服务（例如 DeepSeek 原生 endpoint）需要通过 LiteLLM、OneAPI 或其他协议转换网关接入，`CODEX_MODEL` 填写网关支持的模型名称。

## Label 和触发规则

| Label / 指令 | 驱动的流程 |
| --- | --- |
| `ready-to-spec` | issue 已准备进入 spec 编写。 |
| `ready-to-implement` | issue 已准备进入实现。 |
| `plan-approved` | spec PR 已批准，可作为 implementation 的 spec context。 |
| `@AGENT_LOGIN /review` | 在非 draft PR conversation comment 中手动触发 AI review。 |
| `@AGENT_LOGIN /fix` | 在 PR conversation、PR review 或 inline review comment 中请求 Codex 修复。 |

`ready-to-spec` 和 `ready-to-implement` 是人工维护的阶段门。triage 不会自动添加这两个 label。`plan-approved` 只作为 spec context 的批准信号，不直接触发 implementation workflow。

## Issue Triage

本地创建 issue 时可以使用 `create-issue` SKILL。它根据当前对话或用户输入选择 `.github/ISSUE_TEMPLATE` 模板并创建 issue，但默认不添加分类 labels；issue 打开后由下面的 triage workflow 接管分类、复现度、重复检测和 triage comment。

Workflow：

```text
.github/workflows/triage-issue.yml
```

触发方式：

- issue opened / reopened。
- 非 bot 用户在 issue 上创建 comment。
- 手动 `workflow_dispatch`。

流程：

1. `prepare_issue_triage_context.py` 生成 `triage_context.json`、`issue_comments.txt`、`issue_templates.txt` 和 `dedupe_candidates.json`。
2. Codex 按顺序使用 `triage-issue` 和 `dedupe-issue`，只输出 `triage_result.json`。
3. workflow 校验 JSON。
4. `apply_issue_triage_result.py` 应用 labels，并按需 upsert triage comment。

保留规则：

- `plan-approved`、`ready-to-implement`、`ready-to-spec` 是 protected labels，不由 triage 自动添加或移除。
- `duplicate_of` 和 `follow_up_questions` 互斥。
- 仓库可以用 `triage-issue-repo` 和 `dedupe-issue-repo` 补充本地规则，但不能改变核心输出 schema 和 protected label 规则。

## Create Spec from Issue

Workflow：

```text
.github/workflows/create-spec-from-issue.yml
```

触发条件：

- 手动 `workflow_dispatch`。
- issue 带 `ready-to-spec`，并且被分配给 `AGENT_LOGIN`。
- issue 已带 `ready-to-spec`，并在 issue comment 中 mention `@AGENT_LOGIN`。

如果 issue 已经带有 `ready-to-implement`，spec workflow 不会启动，避免同一个 issue 同时进入 spec 和 implementation 阶段。

流程：

1. 在 workspace 内 `.codex-runtime/handoff/` 准备 `issue_context.json` 和 `issue_comments.txt`，并把具体路径传给 Codex 和后续脚本。
2. Codex 按顺序使用 `spec-driven-implementation`、`write-product-spec`、`create-product-spec`、`write-tech-spec`、`create-tech-spec`。
3. 生成 `specs/issue-<N>/product.md`、`specs/issue-<N>/tech.md`，并把 `pr-metadata.json` 写到同一个 `.codex-runtime/handoff/` 目录。
4. 校验输出后推送 `spec/issue-<N>` 分支并创建或更新 spec PR。

Spec PR 只负责规划，不应该实现功能或修改生产代码。

## Plan Approved

Workflow：

```text
.github/workflows/plan-approved.yml
```

当 spec PR 获得 `plan-approved` label 时，workflow 会解析关联 issue，并移除 `ready-to-spec`。如果 issue 已经带有 `ready-to-implement`，且已分配给 `AGENT_LOGIN`，它会 dispatch `create-implementation-from-issue.yml`；否则只记录 skip reason，不会自动添加 `ready-to-implement`。

## Create Implementation from Issue

Workflow：

```text
.github/workflows/create-implementation-from-issue.yml
```

触发条件：

- 手动 `workflow_dispatch`。
- issue 带 `ready-to-implement`，并且被分配给 `AGENT_LOGIN`。
- issue 已带 `ready-to-implement`，并在 issue comment 中 mention `@AGENT_LOGIN`。

流程：

1. 在 workspace 内 `.codex-runtime/handoff/` 准备 `issue_context.json`、`issue_comments.txt`，有 spec context 时生成 `spec_context.md`。
2. 如果存在关联 spec PR，只有带 `plan-approved` label 的 spec PR 会作为批准的 spec context。
3. 如果发现未批准 spec PR 且默认分支没有 specs，则 workflow noop，并更新 issue progress comment。
4. Codex 按顺序使用 `implement-specs`、`spec-driven-implementation`、`implement-issue`。
5. Codex 留下实现 diff，并把 `implementation_summary.md` 和 `pr-metadata.json` 写到 `.codex-runtime/handoff/`。
6. workflow 校验 metadata，提交并推送实现分支，创建或更新 implementation PR。

目标分支规则：

- 有 approved spec PR：实现追加到该 spec PR 的 head branch，让 spec 和实现留在同一个 PR。
- 没有 approved spec PR：默认使用 `spec/implement-issue-<N>`，也允许 metadata 使用 `spec/implement-issue-<N>-<slug>`。

`pr-metadata.json` 必须包含：

```json
{
  "branch_name": "spec/implement-issue-42-add-retry-logic",
  "pr_title": "fix: add retry logic for transient API failures",
  "pr_summary": "Closes #42\n\n## Summary\n新增 API 重试逻辑。\n\n## Testing\n运行客户端单元测试并通过。\n\n## Risk\n重复请求可能增加 API 负载。\n\n## How to revert\n回退本 PR 提交。",
  "intended_files": [
    "src/api/client.py",
    "tests/test_client.py"
  ]
}
```

`pr_summary` 第一行必须是 `Closes #<issue-number>`，并填写非空的 `## Summary`、`## Testing`、`## Risk`、`## How to revert` 四个章节。`intended_files` 必须精确列出 workflow 应提交的实现文件，不包含临时文件、validation logs、生成缓存或未变化文件。

## 夜间存量代码审查

`review-existing-code.yml` 每天北京时间 02:30 运行。每次先查看默认分支的完整代码清单、入口和跨文件调用链，再深入审查当天的重点文件。默认轮巡周期为 7 天；设置 Actions variable `NIGHTLY_REVIEW_CYCLE_DAYS` 可调整为 1–90 天。`workflow_dispatch` 可临时覆盖周期，并指定 `0` 至“周期天数减 1”的分片补跑；留空时使用当天的北京时间分片。源码、工作流、脚本和可执行的技能说明是审查目标，测试和其他文件用于核实发现。稀疏项目遇到空分片时会复查一个文件，确保每天仍执行项目级审查。

审查 Agent 只读取固定提交的项目代码清单、重点文件及已有 Issue 快照，输出 `nightly-review-output/findings.json`。它不直接发布 Issue。若跨文件调查定位到重点范围外的根因，也可报告该项目代码位置。外层工作流校验文件位置、输入完整性和写入范围，并按现有 Issue 与稳定指纹查重。只有具备明确触发条件、影响和核实依据的高置信缺陷才会逐项创建中文 Issue。公开的安全 Issue 不应包含利用载荷或敏感信息。无发现时不创建 Issue；运行产物始终上传，失败运行不会发布未经校验的结果。

调度由 GitHub Actions 执行；如某天未运行，可从 Actions 页面手动补跑对应分片。该流程不修改源码，也不使用 PR review 的差异行定位契约。

## PR Review

Workflow：

```text
.github/workflows/review-pr.yml
```

AI PR Review 会：

1. preflight 确认 PR 是 open；自动 PR 事件要求 same-repo、非 draft，新建 implementation PR 的显式分发可审查 draft。
2. 生成稳定的 `pr_description.txt`。
3. 生成带行号的 `pr_diff.txt`。
4. 如果能找到相关 spec，生成 `spec_context.md`。
5. 纯 `specs/` PR 使用 `review-spec`；其他 PR 使用 `review-pr`。
6. `review-pr` 在存在 `spec_context.md` 时加载 `check-impl-against-spec`。
7. 输出并验证 `review.json`。
8. 通过 GitHub API 发布 PR review。

每次 Action 只执行一次 Review。流程按同一 PR 已发布 Review 的不同 base/head SHA 快照
计算轮次；相同快照重跑在 AI 审查前跳过。前三轮对比当轮 base 和当前 head 的完整 PR diff；第四轮起在历史提交可追溯
且 base 未变化时重点比较上次已审查 head 与当前 head 的 diff，并审视反复局部修复是否需要调整整体方案。
CI 在非草稿 PR 更新和 merge queue 检查时运行测试，不校验 PR 正文；
仅编辑正文不会重新运行 CI。
自动审查由 `pull_request_target` 直接触发，不等待 CI 结果；`workflow_dispatch`
和 PR 评论命令保留作手动触发入口。使用 `GITHUB_TOKEN` 创建或更新 PR 的工作流
通过 `workflow_dispatch` 显式分发；CI 不再自动分发审查。
如果当前 head 已发布 Review，重跑会跳过 AI 生成并恢复该 head 的审查状态。

发布规则：

- 内部成员、协作者或 owner PR 的 `REJECT` 发布为普通 `COMMENT` review，不产生 GitHub blocking review。
- 外部 contributor 的 code PR 在 `REJECT` 时发布 `REQUEST_CHANGES`；是否阻塞 merge 取决于目标仓库 branch protection。
- 外部 contributor 的 code PR 后续变为 `APPROVE` 时，workflow 会尝试 dismiss 旧的 bot-authored `REQUEST_CHANGES` review。默认只清理 `github-actions[bot]` 发出的 review；如果仓库改用其他 bot 账号发布 review，请设置 `REVIEW_BOT_LOGIN` 为该账号 login。
- spec-only PR 的 `REJECT` 始终发布为普通 `COMMENT` review。

`spec_context.md` 的查找顺序：

1. 找到当前 PR 关联 issue。
2. 优先查找 `spec/issue-<N>` 分支上的 open PR，并要求带 `plan-approved` label。
3. 如果没有 approved spec PR，则从 PR base commit/ref 上读取 `specs/issue-<N>/product.md` 和 `tech.md`。
4. 如果都没有，就不生成 `spec_context.md`。

## 处理 PR Comments

Workflow：

```text
.github/workflows/respond-to-pr-comment.yml
```

触发方式：

- PR conversation comment 中包含 `@AGENT_LOGIN` 和 `/fix`。
- inline review comment 中包含 `@AGENT_LOGIN` 和 `/fix`。
- PR review body 中包含 `@AGENT_LOGIN` 和 `/fix`。

流程：

1. `prepare_pr_comment_context.py` 先生成稳定 context，workflow checkout PR head 后把这些 context 放到 `pr-worktree/.codex-runtime/handoff/`。
2. workflow 在 `pr-worktree/.codex-runtime/handoff/` 生成 `pr_diff.txt` 和可选 `spec_context.md`。
3. Codex 使用 `implement-specs`、`spec-driven-implementation`、`implement-issue`，按触发 comment 的范围做最小修复。
4. Codex 把 `implementation_summary.md`、`pr-metadata.json`，以及必要时的 `resolved_review_comments.json` 写到 `pr-worktree/.codex-runtime/handoff/`。
5. workflow 校验输出，提交并推送到原 PR 分支或 agent response branch。
6. `apply_pr_comment_result.py` 发布总结，并在有权限和有效 comment id 时处理 resolved review comments。
7. 使用 `GITHUB_TOKEN` 推送非 draft PR 时显式分发 AI PR Review；使用 GitHub App token 推送 workflow 文件时由 PR 事件触发。新建的 follow-up draft PR 暂不审查。

当请求要求处理“所有 inline comments”“所有 unresolved comments”或某类 comments 时，Codex 会读取 `review_comment_ids.json`，而不是只处理触发 comment 本身。`is_outdated` 只表示原始 diff 位置过期，不代表问题已经解决。

## 常用 Artifact

排查 PR review 问题时优先查看：

```text
pr_description.txt
pr_diff.txt
spec_context.md
review.json
```

排查 implementation 或 `/fix` 问题时优先查看：

```text
issue_context.json
issue_comments.txt
pr_comment_context.json
review_comment_ids.json
spec_context.md
implementation_summary.md
pr-metadata.json
resolved_review_comments.json
validation-output.txt
validation-error.txt
```

这些 implementation、spec 和 `/fix` handoff artifact 由 workflow 放在 workspace 内 `.codex-runtime/handoff/` 或 `pr-worktree/.codex-runtime/handoff/` 目录中，artifact 上传仍保留文件名；workflow 的提交和变更检查会排除 `.codex-runtime/`，因此不再依赖仓库根目录 `.gitignore` 来隐藏 scratch 文件。Spec workflow 当前只定义 issue context、comments 和 PR metadata handoff，不定义单独 summary 或 validation-log handoff。
