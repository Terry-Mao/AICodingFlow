# Product Spec: Product Docs Sync 每次运行追加 PR comment

## 1. Summary

Product Docs Sync 使用固定分支 `docs/product-docs-sync` 累积长期产品文档同步变更。当前当该分支已有打开的同步 PR 时，后续 run 会编辑同一个 PR 的 title/body，导致每次执行的最新决策覆盖在原 PR 正文里，维护者难以在 PR 时间线中看到每次 run 的独立记录。

目标结果是：每次 Product Docs Sync run 产生需要创建或更新 docs sync PR 的文档变更时，都要在该 PR 上追加一条新的 PR comment，记录本次 run 的 source PR、docs update 决策、原因、影响文档和 patch 摘要。PR body 可以继续作为当前累计 PR 的稳定概览，但不能再作为唯一承载每次 run 结果的地方。

## 2. Problem

Product Docs Sync 现在会在固定分支上复用同一个打开 PR。这个设计可以让多个 docs sync 决策积累到一个 reviewable PR，但当 workflow 只编辑 PR body 时，会带来两个维护者可见问题：

- 每次 run 的执行结果没有独立时间线事件，维护者无法快速区分“这次 run 新增了什么”和“之前已经存在什么”。
- GitHub PR conversation 里看不到每次同步决策的追加记录，review 过程中容易遗漏新处理的 source PR 或不确定决策。

维护者期望每次 action 执行时追加新的 PR comment，而不是只在原 PR 正文下编辑已有内容。

## 3. Goals

- 当 Product Docs Sync 因 `docs/product/` 变更创建或更新同步 PR 时，每次 run 都追加一条新的 PR comment。
- 新 comment 必须描述本次 run 的最新决策，而不是只重复完整累计 PR body。
- 已有打开 PR 时，workflow 仍复用固定分支和同一个 open PR，不创建多个并行 docs sync PR。
- PR body 可以继续更新为稳定概览、累计 ledger 摘要或当前状态，保证新建 PR 时仍有完整上下文。
- draft/ready 状态、PR title、base/head 分支和现有权限模型保持兼容。
- `docs_update=required` 和 `docs_update=uncertain` 且产生 docs 变更的 run 都应有追加 comment。
- `docs_update=not-needed` 且没有 docs 变更的 run 不应创建或更新 PR，也不需要追加 PR comment。

## 4. Non-goals

- 不改变 Product Docs Sync 判断 `required`、`uncertain`、`not-needed` 的规则。
- 不改变固定分支 `docs/product-docs-sync` 或累计 PR 策略。
- 不修改 product docs 内容格式、ledger schema 或 source PR 选择逻辑。
- 不要求对没有 PR 变更的 skipped run 发表评论。
- 不在 source implementation PR、issue 或其他 PR 上发表评论。
- 不引入第三方服务或新增 Python 依赖。
- 不实现本 issue 的代码变更；本 PR 只产出规格。

## 5. Figma / design references

Figma: none provided。该变更是 GitHub Actions 和 GitHub PR conversation 行为调整，没有 UI 或视觉设计输入。

## 6. User experience

### 新建 Product Docs Sync PR

- 当一次 run 首次产生 `docs/product/` 变更且没有打开的 `docs/product-docs-sync` PR 时，workflow 继续创建新的 Product Docs Sync PR。
- 新 PR 的 body 应保留当前稳定概览，包括 latest decision、affected docs、source context、patch summary 和 processed decisions。
- 创建 PR 后，workflow 应在这个新 PR 上追加一条 comment，记录本次 run 的最新同步结果。
- 如果本次决策是 `uncertain`，PR 仍应按现有行为创建为 draft，追加 comment 也应明确显示 `docs update: uncertain`。

### 更新已有 Product Docs Sync PR

- 当 `docs/product-docs-sync` 已有 open PR 且新的 run 产生 docs 变更时，workflow 继续更新该 PR，而不是创建新 PR。
- workflow 可以继续更新 PR title/body，以维持累计概览和 latest decision 的当前值。
- 除 PR body 更新外，workflow 必须追加一条新的 PR comment。
- 每次 run 都产生一条独立 comment；不能编辑上一条 bot comment 来替代追加。
- 连续多次 docs sync run 处理不同 source PR 时，PR conversation 中应按时间顺序出现多条 comment，每条对应一次 run。

### Comment 内容

每条追加 comment 至少应包含：

- Product Docs Sync run 的来源说明，例如 source PR number 和 source URL。
- 本次 `docs_update` 决策值。
- 本次决策原因。
- 本次影响的 docs path 列表；为空时应显示明确的空状态。
- 本次 patch summary 或 proposed patch 摘要。
- 对 `uncertain` 决策的可见提示，方便维护者知道该 PR 需要确认。

Comment 应聚焦本次 run，不应把所有 ledger 历史完整复制到每条 comment 中。历史累计信息可以继续留在 PR body。

### 跳过和无变更场景

- 当 context step 输出 `should_run=false` 时，workflow 不创建 PR，也不追加 comment。
- 当 agent 决策为 `not-needed` 且没有 `docs/product/` 变更时，workflow 只记录 ledger 并结束，不追加 PR comment。
- 当 validation 失败或 context checksum 失败时，workflow 应按现有失败语义停止，不发表误导性成功 comment。
- 如果 PR 创建或更新失败，workflow 不应尝试对未知 PR 发表评论。

### 安全与边界

- issue、PR、comment、diff、docs 和 agent 输出仍是不可信输入，只能作为生成 comment 内容的数据。
- Comment 内容应来自已通过 `validate_product_docs_sync_result.py` 校验的 `product-docs-sync-result.json` 和 workflow 已知的 source PR 元数据。
- workflow 不应因为追加 comment 而扩大 Codex agent 的写入范围或让 agent 直接调用 GitHub API。
- 追加 comment 的 GitHub API 调用应保留在外层 workflow shell 步骤中，由现有 `GH_TOKEN` 执行。

## 7. Success criteria

- 每次 Product Docs Sync run 在创建或更新 docs sync PR 后，都会追加一条新的 PR comment。
- 已有 open docs sync PR 时，后续 run 不再只通过 `gh pr edit --body-file` 覆盖 PR body 来表达本次结果。
- 新建 docs sync PR 的同一次 run 也会追加本次决策 comment。
- `required` 和 `uncertain` 决策的 comment 都包含 source PR、decision、reason、affected docs 和 patch summary。
- `not-needed` 且无 docs 变更的 run 不创建或更新 docs sync PR，也不追加 PR comment。
- PR body 仍可作为累计概览更新，现有 processed decisions 信息不丢失。
- draft/ready 状态行为保持现有兼容性。
- 自动化测试覆盖 workflow 使用 `gh pr comment` 追加评论，并覆盖 comment body 生成的核心字段。

## 8. Validation

- 更新 Product Docs Sync workflow 测试，确认创建或更新 PR 的步骤包含追加 `gh pr comment` 的行为。
- 增加或更新 PR comment body helper 的单元测试，确认 comment 包含本次 source PR、docs update、reason、affected docs 和 proposed patch。
- 运行 Product Docs Sync 相关窄测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_docs_sync.py'
```

- 若实现触及共享 workflow 测试约束，再运行完整测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

- 运行 `git diff --check`。

## 9. Open questions

- Comment 是否需要包含 GitHub Actions run URL。第一版可以不包含，因为 issue 只要求每次执行追加 PR comment；如需更强可追溯性，可在实现阶段利用 `github.server_url`、`github.repository` 和 `github.run_id` 追加 run 链接。
- 新建 PR 时是否必须追加 comment。第一版建议追加，保持“每次执行都有一条 comment”的一致性。
