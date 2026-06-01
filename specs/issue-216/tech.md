# Tech Spec: Product Docs Sync 追加每次运行 PR comment

## 1. Problem

`.github/workflows/product-docs-sync.yml` 在 `docs/product/` 有变更时会创建或更新固定分支 `docs/product-docs-sync` 的 PR。当前已有 open PR 时，workflow 调用 `gh pr edit --body-file` 更新同一个 PR 的 body，并调整 draft/ready 状态；没有额外的 `gh pr comment` 步骤记录本次 run。

技术目标是在不改变 docs sync agent、ledger、分支策略和 PR 复用策略的前提下，让外层 workflow 在每次创建或更新 docs sync PR 后追加一条描述本次 run 的 PR comment。

## 2. Relevant code

- `.github/workflows/product-docs-sync.yml` — Product Docs Sync workflow；`Create or update product docs sync pull request` step 负责 commit、push、生成 PR body、查找 existing PR、`gh pr edit` 或 `gh pr create`。
- `.github/scripts/write_product_docs_sync_pr_body.py` — 当前根据 `product-docs-sync-result.json`、source PR env 和 ledger 生成 PR body；`build_body()` 包含 latest decision 和 processed decisions。
- `.github/scripts/update_product_docs_sync_ledger.py` — 在 PR 创建/更新前把本次决策写入 `docs/product/.product-docs-sync-ledger.json`，供 PR body 汇总历史决策。
- `.github/scripts/validate_product_docs_sync_result.py` — 校验 agent result schema 和 write surface；只有通过校验后 workflow 才更新 ledger 和 PR。
- `.github/aicodingflow-tests/test_product_docs_sync.py` — 覆盖 body writer、validator、ledger 和 workflow YAML，应扩展为覆盖新增 comment body 和 workflow `gh pr comment` 行为。

## 3. Current state

当前 PR 创建/更新流程：

1. workflow 确认 `steps.context.outputs.should_run == 'true'` 且 `steps.changes.outputs.changed == 'true'`。
2. 根据 `DOCS_UPDATE` 设置 PR title，`uncertain` 使用 draft title。
3. `git add docs/product`、commit、push 到 `docs/product-docs-sync`。
4. 调用 `write_product_docs_sync_pr_body.py --result product-docs-sync-result.json --output "$body_file"` 生成 PR body。
5. 通过 `gh pr list --head "$branch" --state open` 查找已有 PR。
6. 已有 PR 时执行 `gh pr edit "$existing_pr" --title "$title" --body-file "$body_file"`，并根据 `DRAFT` 调整 ready/draft。
7. 没有 PR 时执行 `gh pr create ... --body-file "$body_file"`。

缺口在第 6 和第 7 步之后：workflow 没有为本次 run 发布新的 PR comment。虽然 PR body 的 “Latest decision” 会更新，ledger 历史也会被汇总，但 PR conversation 没有每次 run 的追加事件。

## 4. Proposed changes

### 新增本次运行 comment body 生成能力

在 `.github/scripts/write_product_docs_sync_pr_body.py` 中新增一个聚焦单次 run 的 body builder，例如：

```python
def build_comment(pr_number: str, pr_url: str, result: dict[str, Any]) -> str:
    ...
```

该函数应复用现有格式化 helper，输出只描述最新 result，不展开整个 ledger。建议结构：

```markdown
Product Docs Sync processed a source PR.

- source PR: #123
- docs update: `required`
- reason: ...
- source URL: ...

Affected docs:
- `docs/product/raw/example.md`

Patch summary:
...
```

要求：

- `affected_docs` 为空时输出明确空状态，例如 `- none`，避免生成空 section。
- `source_context` 可以可选包含，但不能让 comment 变成长篇历史 ledger。
- `proposed_patch` 缺失或为空时输出空字符串或明确空状态，保持 markdown 可读。
- 不新增外部依赖，继续使用 Python 标准库。

### 扩展脚本 CLI

给 `.github/scripts/write_product_docs_sync_pr_body.py` 增加可选输出参数，避免新增重复脚本。例如：

```bash
python3 .github/scripts/write_product_docs_sync_pr_body.py \
  --result product-docs-sync-result.json \
  --output "$body_file" \
  --comment-output "$comment_file"
```

实现方式：

- 保持 `--output` 现有语义不变，继续写 PR body。
- 新增 `--comment-output` 可选参数；提供时写入 `build_comment(...)` 的结果。
- `main()` 继续从 `SOURCE_PR_NUMBER`、`SOURCE_PR_URL` 和 `LEDGER_PATH` 获取现有上下文。
- 不改变 `build_body()` 输出，除非测试需要微调空列表格式。

如果实现阶段更倾向新增独立脚本，也可以接受，但复用现有 result parsing 和 source PR env 更符合当前代码结构。

### 修改 workflow PR 创建/更新步骤

在 `.github/workflows/product-docs-sync.yml` 的 `Create or update product docs sync pull request` step 中：

1. 同时创建 `body_file` 和 `comment_file`，并在 trap 中清理。
2. 调用 body writer 时传入 `--comment-output "$comment_file"`。
3. 统一得到目标 PR 编号：
   - 已有 PR 分支：`target_pr="$existing_pr"`。
   - 新建 PR 分支：使用 `gh pr create --json number --jq '.number' ...` 获取新 PR number，赋给 `target_pr`。
4. PR edit/create 和 ready/draft 处理完成后，执行：

```bash
gh pr comment "$target_pr" \
  --repo "${{ github.repository }}" \
  --body-file "$comment_file"
```

关键边界：

- comment 必须在 PR number 已知后发布。
- 已有 PR 和新建 PR 都应走同一个 `gh pr comment` 路径。
- 不使用 `gh pr edit` 或任何 marker 查找旧 comment 来更新；每次 run 都新增 comment。
- 如果 `gh pr create` 失败，shell 应按 `set -e` 语义停止，不发布 comment。
- 保留现有 `DRAFT` ready/undo 逻辑。Comment 可以在 ready/draft 调整之后发布，降低状态调整失败后留下成功 comment 的概率。

### 权限和安全

现有 workflow 已有：

```yaml
permissions:
  contents: write
  pull-requests: write
```

`gh pr comment` 仍属于 PR 写入操作，预计不需要新增权限。实现不应让 Codex agent 直接调用 GitHub API；agent 只产出 `product-docs-sync-result.json` 和 docs diff，外层 workflow 在校验后生成并发布 comment。

Comment body 来自已校验 result 和 workflow env。实现不应把 issue、PR description、diff 或评论中的内容当作 shell 命令拼接；通过 `--body-file` 传给 `gh pr comment`，避免 shell quoting 风险。

## 5. End-to-end flow

1. Product Docs Sync 选择一个 merged source PR 并运行 docs sync agent。
2. `validate_product_docs_sync_result.py` 校验 result 和 write surface。
3. `update_product_docs_sync_ledger.py` 记录本次 source PR 决策。
4. workflow 检测 `docs/product/` 有变更，commit 并 push 到 `docs/product-docs-sync`。
5. body writer 生成：
   - PR body：累计概览和 processed decisions。
   - PR comment body：只描述本次 run。
6. workflow 查找 open docs sync PR。
7. 如果已有 PR，更新 title/body 和 draft/ready 状态，并把 PR number 设为目标。
8. 如果没有 PR，创建新 PR，读取新 PR number，并把它设为目标。
9. workflow 对目标 PR 调用 `gh pr comment --body-file "$comment_file"`。
10. PR conversation 中出现一条新的 Product Docs Sync run comment；后续 run 会追加新的 comment。

## 6. Risks and mitigations

- 风险：`gh pr create` 默认输出不是稳定可解析 PR number。
  - 缓解：使用 `--json number --jq '.number'` 获取新 PR 编号，而不是解析 human-readable 输出。
- 风险：已有 PR 分支和新建 PR 分支各自实现 comment，后续行为分叉。
  - 缓解：把目标 PR 编号写入统一变量 `target_pr`，在 if/else 之后只调用一次 `gh pr comment`。
- 风险：comment body 复制完整 ledger，导致每次评论过长。
  - 缓解：新增单次 run builder，PR body 继续承担累计历史，comment 只承担本次决策。
- 风险：未通过校验的 agent 输出被评论到 PR。
  - 缓解：workflow 顺序保持 `Validate product docs sync result` 在 ledger、commit、PR 和 comment 之前。
- 风险：shell quoting 导致 markdown 中的特殊字符被解释。
  - 缓解：通过临时文件和 `--body-file` 传递 body，不在 shell 命令里内联 markdown。
- 风险：comment 发布成功但后续步骤失败。
  - 缓解：将 `gh pr comment` 放在 PR edit/create、ready/draft 状态调整之后，并保持 step fail-fast。

## 7. Testing and validation

在 `.github/aicodingflow-tests/test_product_docs_sync.py` 中增加或更新覆盖：

- `build_comment()` 单元测试：
  - 包含 `source PR: #...`、`docs update: \`...\``、reason、source URL、affected docs 和 proposed patch。
  - 覆盖 `affected_docs=[]` 时输出 `none` 或等价空状态。
- `main()` CLI 测试：
  - 传入 `--comment-output` 时同时写出 PR body 和 comment body。
  - 不传 `--comment-output` 时保持现有只写 PR body 行为。
- workflow YAML 测试：
  - `Create or update product docs sync pull request` step 包含 `--comment-output "$comment_file"`。
  - step 包含 `gh pr comment "$target_pr"` 或等价的统一目标 PR comment 调用。
  - 新建 PR 路径使用 `gh pr create --json number --jq '.number'` 或其他稳定方式取得 PR number。
  - 已有 PR 路径仍保留 `gh pr edit` 和 draft/ready 逻辑。

推荐运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_docs_sync.py'
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile .github/scripts/write_product_docs_sync_pr_body.py
git diff --check
```

如果实现调整了共享 workflow contract 或测试 helper，再运行完整 suite：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

## 8. Follow-ups

- 可后续在 comment 中加入 Actions run URL，增强从 PR conversation 追溯到具体 workflow run 的能力。
- 如果 Product Docs Sync comment 后续变多，可另开 issue 设计可折叠 summary 或 comment grouping；本 issue 明确要求每次 run 追加 comment，因此不做去重或编辑旧评论。
