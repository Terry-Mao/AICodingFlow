# Tech Spec: Product Docs Sync missing issue reference 容错

## 1. Problem

`.github/scripts/prepare_product_docs_sync_context.py` 在准备 Product Docs Sync 上下文时，会从目标 PR 提取 issue 编号，然后对每个编号调用 `fetch_issue()`。`fetch_issue()` 通过 `gh issue view` 获取 issue JSON；当 PR 引用了不存在或不可读取的 issue 时，GitHub CLI 返回非零状态，`subprocess.run(check=True)` 抛出异常，脚本中断。

技术目标是在 linked issue fetch 路径上对单个 missing issue reference 做容错：跳过失败的 issue，继续为目标 PR 生成稳定上下文，同时保留其他错误路径的现有失败语义。

## 2. Relevant code

- `.github/scripts/prepare_product_docs_sync_context.py:25` — `run_gh_json()` 使用 `subprocess.run(..., check=True)` 调用 GitHub CLI。
- `.github/scripts/prepare_product_docs_sync_context.py:212` — `fetch_issue()` 封装 `gh issue view <number>`，当前不捕获失败。
- `.github/scripts/prepare_product_docs_sync_context.py:233` — `issue_numbers()` 从 `closingIssuesReferences`、PR 标题和正文中的引用关键词提取去重 issue 编号。
- `.github/scripts/prepare_product_docs_sync_context.py:296` — `read_specs()` 根据 issue 编号读取 `specs/issue-<number>/product.md` 和 `tech.md`。
- `.github/scripts/prepare_product_docs_sync_context.py:318` — `write_context_json()` 把 `linked_issues` 和 specs 写入 JSON 上下文。
- `.github/scripts/prepare_product_docs_sync_context.py:342` — `write_markdown()` 渲染 linked issue 详情。
- `.github/scripts/prepare_product_docs_sync_context.py:474` — `main()` 当前通过 `[fetch_issue(args.repo, number) for number in numbers]` 一次性读取全部 issue；任意失败都会中断。
- `.github/aicodingflow-tests/test_product_docs_sync.py:36` — Product Docs Sync 脚本测试类，已有 issue 编号提取、ledger、workflow 和 validator 覆盖。

## 3. Current state

当前数据流：

1. `main()` 选择待处理 PR。
2. `issue_numbers(pr)` 返回去重后的 issue 编号列表。
3. `issues = [fetch_issue(args.repo, number) for number in numbers]` 逐个读取 linked issue。
4. `read_specs(root, numbers)` 根据原始编号列表读取 specs。
5. `write_context_json()` 和 `write_markdown()` 写出 PR、linked issue、specs 和 product docs 上下文。

失败点在第 3 步：`fetch_issue()` 没有区分“单个 linked issue 不存在”和“脚本无法继续”的错误。由于列表推导没有局部异常处理，任何 `gh issue view` 失败都会阻止后续 diff、docs 和 ledger 流程。

## 4. Proposed changes

### 新增容错读取 helper

在 `.github/scripts/prepare_product_docs_sync_context.py` 中增加一个小 helper，例如：

```python
def fetch_existing_issues(repo: str, numbers: list[int]) -> tuple[list[dict[str, Any]], list[int]]:
    issues: list[dict[str, Any]] = []
    skipped: list[int] = []
    for number in numbers:
        try:
            issues.append(fetch_issue(repo, number))
        except subprocess.CalledProcessError:
            skipped.append(number)
    return issues, skipped
```

实现可按现有脚本风格调整命名，但应满足：

- 只包住单个 `fetch_issue()` 调用。
- 捕获 `subprocess.CalledProcessError`，因为这是 `run_gh_json()` 当前对 GitHub CLI 非零退出的实际异常。
- 不捕获 JSON 解析错误、文件写入错误、ledger 错误或其他脚本 bug。
- 返回成功读取的 issue 列表，并可返回 skipped 编号供调试或后续扩展使用。

### 调整 main 数据流

把当前列表推导替换为容错 helper：

```python
numbers = issue_numbers(pr)
issues, skipped_issue_numbers = fetch_existing_issues(args.repo, numbers)
existing_issue_numbers = [int(issue.get("number")) for issue in issues if issue.get("number")]
specs = read_specs(root, existing_issue_numbers)
```

关键边界：

- `issues` 只包含成功读取的 issue。
- `read_specs()` 应基于成功读取的 issue 编号，而不是原始 `numbers`，避免 missing issue 编号意外拉入本地同名旧 specs。
- 如果没有成功读取任何 issue，`issues` 和 `specs` 都可以为空列表，workflow 仍继续。
- `should_run` 仍保持 `true if pr.get("mergedAt") else "false"` 的现有逻辑。

`skipped_issue_numbers` 第一版可以只用于简短 stderr/stdout 日志，避免扩大 JSON context schema。如果选择写入日志，保持纯诊断性质，不影响输出 contract。

### 保持不变

不修改以下行为：

- `issue_numbers()` 的关键词和去重规则。
- `fetch_pr()`、`fetch_merged_prs()`、`fetch_pr_diff()` 的失败语义。
- `write_context_json()` 的顶层 schema。
- `write_markdown()` 对 linked issue 的渲染格式。
- Product Docs Sync workflow YAML、Codex prompt、permissions、ledger schema 和 allowed write roots。

## 5. End-to-end flow

1. Product Docs Sync 选中一个 merged PR。
2. `issue_numbers(pr)` 从 PR metadata 和正文中提取编号，例如 `[214, 999999]`。
3. `fetch_existing_issues()` 逐个调用 `fetch_issue()`。
4. issue `214` 成功读取后进入 `issues`。
5. issue `999999` 的 `gh issue view` 返回非零状态，被记录为 skipped 并继续循环。
6. `read_specs()` 只读取成功 issue 编号对应的 specs。
7. JSON 和 markdown context 正常写出，其中 `linked_issues` 只包含 issue `214`。
8. 后续 diff、existing docs、GitHub outputs、Codex docs sync 和 ledger 流程按现有逻辑继续。

## 6. Risks and mitigations

- 风险：捕获过宽导致真实 GitHub CLI 故障被静默跳过。
  - 缓解：只在 linked issue fetch helper 中捕获 `subprocess.CalledProcessError`；其他阶段仍失败。
- 风险：GitHub CLI 因认证或网络问题读取所有 issue 都失败，workflow 继续但上下文缺少 issue。
  - 缓解：当前需求明确要求跳过 missing issue reference；实现可输出 skipped 编号诊断，后续如需区分 exit code 或 stderr 可另开增强。
- 风险：仍按原始 issue 编号读取 specs，会把不存在 issue 的本地 spec 加进上下文。
  - 缓解：`read_specs()` 改用成功读取 issue 的编号列表。
- 风险：新增 skipped issue 字段破坏下游 context consumer。
  - 缓解：第一版不改变 `write_context_json()` schema，只调整内部读取流程。
- 风险：测试只覆盖 helper，不覆盖 main 写出路径。
  - 缓解：增加至少一个围绕 `main()` 或上下文写出路径的测试，断言脚本继续写文件且 linked issues 过滤正确。

## 7. Testing and validation

在 `.github/aicodingflow-tests/test_product_docs_sync.py` 增加测试覆盖：

- `fetch_existing_issues()` 在第二个 issue 抛出 `subprocess.CalledProcessError` 时返回第一个 issue，并记录 skipped 编号。
- `main()` 或接近 main 的集成式测试中，构造 PR 引用两个 issue，mock `fetch_issue` 对其中一个编号抛出 `CalledProcessError`，确认：
  - 脚本返回成功。
  - `product-docs-sync-context.json` 存在。
  - `linked_issues` 只包含成功读取的 issue。
  - specs 只读取成功 issue 编号对应目录。
  - `should_run` 输出仍由 merged PR 状态决定。

推荐运行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_docs_sync.py'
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile .github/scripts/prepare_product_docs_sync_context.py
git diff --check
```

如果实现过程中调整了共享测试 helper 或 workflow contract，再运行完整 suite：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

## 8. Follow-ups

- 如果维护者需要更强可观测性，可在后续 issue 中为 context JSON 增加 `skipped_issue_references` 字段，并同步更新 docs sync prompt 和 tests。
- 如果需要区分 not found、权限不足、rate limit、网络错误，可后续扩展 `run_gh_json()` 返回 stderr 或引入更细粒度错误分类。
