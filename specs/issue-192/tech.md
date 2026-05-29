# Tech Spec: Product Docs Sync 每小时调度

## 1. Problem

Product Docs Sync workflow 目前通过 `schedule` 每天运行一次，但其扫描路径每次只选择一个尚未处理的 merged PR。这个吞吐模型与日频调度不匹配：当 merged PR 多于每天一个时，product docs sync ledger 会落后，后续 docs update 决策和长期产品文档同步都可能积压。

技术目标是只调整 Product Docs Sync 的定时 cadence，让 scheduled run 每小时触发，同时保持现有手动触发、context selection、ledger、concurrency、Codex prompt 和写入边界不变。

## 2. Relevant code

- `.github/workflows/product-docs-sync.yml` — Product Docs Sync workflow 入口；当前包含 `workflow_dispatch` inputs 和 `schedule` cron。
- `.github/workflows/product-docs-sync.yml` — `concurrency.group: product-docs-sync` 和 `cancel-in-progress: false` 控制定时任务并发行为。
- `.github/scripts/prepare_product_docs_sync_context.py` — scheduled run 未提供 `pr_number` 时扫描 merged PR，读取 ledger，并通过 `select_unprocessed_pr` 返回第一个未处理 PR。
- `.github/scripts/update_product_docs_sync_ledger.py` — docs sync run 完成后记录 PR 处理结果，供后续 scheduled run 跳过。
- `.github/scripts/validate_product_docs_sync_result.py` — 校验 agent 输出和写入边界，确保调度变化不会扩大持久写入范围。
- `.github/aicodingflow-tests/test_product_docs_sync.py` — Product Docs Sync workflow 和脚本的现有单元测试；应增加或更新 schedule cadence 断言。
- `.github/aicodingflow-tests/test_review_workflow_dispatch.py` — 检查 workflows 的 dispatch job 名称映射，预计无需修改，除非 workflow 名称或 job id 发生变化。

## 3. Current state

`product-docs-sync.yml` 当前配置：

- `workflow_dispatch` 支持 `pr_number`、`scan_days`、`start_date` 和 `end_date`。
- `schedule` 为 `45 2 * * *`，即每天 UTC 02:45 运行。
- workflow 在 default branch 上初始化固定分支 `docs/product-docs-sync`。
- context step 调用 `prepare_product_docs_sync_context.py`。
- 当 `steps.context.outputs.should_run != 'true'` 时停止。
- 当需要处理 PR 时，后续步骤运行 Codex docs sync、校验结果、更新 ledger，并在 `docs/product` 有变化时创建或更新 PR。

`prepare_product_docs_sync_context.py` 的扫描路径在未指定 `--pr-number` 时：

- 根据 `scan_days` 或显式日期窗口搜索 merged PR。
- 排除 Product Docs Sync 自己创建的 PR。
- 按 merged time 和 PR number 排序。
- 调用 `select_unprocessed_pr`，遇到 ledger 已记录的 PR 就加入 skipped 列表，返回第一个未处理 PR。
- 如果没有未处理 PR，写出空上下文并通过 GitHub output 设置 `should_run=false`。

因此本 issue 不需要改变 Python 脚本的选择逻辑；需要改变的是 scheduled run 触发频率。

## 4. Proposed changes

### Workflow schedule

在 `.github/workflows/product-docs-sync.yml` 中把 Product Docs Sync 的 cron 从日频改为小时频：

```yaml
schedule:
  - cron: "45 * * * *"
```

选择保留第 45 分钟，以最小化行为变化：只有小时字段从固定 `2` 改为 `*`。这仍然是 GitHub Actions 支持的标准 cron 表达式，并会在每小时 UTC 第 45 分触发。

### 保持不变的行为

实现不应修改以下内容：

- `workflow_dispatch` inputs。
- workflow permissions。
- `concurrency` 配置。
- `Prepare product docs sync context` step 的参数。
- Codex action prompt 和 allowed write surface。
- ledger update、result validation、PR 创建或 artifact upload 流程。
- `.github/scripts/prepare_product_docs_sync_context.py` 的 PR selection 逻辑。

### Tests

更新 `.github/aicodingflow-tests/test_product_docs_sync.py` 中的 workflow schedule 覆盖：

- 在现有 `test_workflow_runs_on_schedule_and_manual_dispatch` 中保留 manual dispatch 和 schedule 存在性断言。
- 增加 cron 值断言，确认 schedule entries 包含 `{"cron": "45 * * * *"}`，或等价地确认第一个 schedule cron 为 `"45 * * * *"`。
- 保留不包含 `pull_request` trigger、permissions 和 workflow dispatch inputs 的断言。

如果测试 helper 使用 PyYAML 解析 workflow，cron 字符串应保持带引号，避免 `*` 或 YAML 解析歧义。

## 5. End-to-end flow

1. GitHub Actions 在每小时 UTC 第 45 分触发 `Product Docs Sync`。
2. workflow checkout default branch，并初始化或 rebase `docs/product-docs-sync` 分支。
3. context script 扫描默认窗口内的 merged PR。
4. script 读取 `docs/product/.product-docs-sync-ledger.json`，跳过已处理 PR。
5. script 选择第一个未处理 PR：
   - 如果存在，输出 `should_run=true` 和该 PR 的稳定上下文。
   - 如果不存在，输出 `should_run=false` 和 skip reason。
6. `should_run=true` 时，后续 docs sync 流程按现有步骤执行，并在完成后更新 ledger。
7. 下一小时 scheduled run 再次扫描同一窗口时，会跳过 ledger 已记录 PR，并处理下一个未处理 PR。

## 6. Risks and mitigations

- 风险：每小时运行增加 GitHub Actions 用量。
  - 缓解：没有未处理 PR 时 workflow 在 context step 后停止；已有 `should_run=false` 跳过机制会避免 Codex 和 PR 创建步骤继续运行。
- 风险：前一次 run 尚未完成时下一次 scheduled run 开始。
  - 缓解：保留 `concurrency.group: product-docs-sync` 和 `cancel-in-progress: false`，避免并发改写同一 docs sync 分支。
- 风险：更高频运行重复处理同一个 PR。
  - 缓解：保留 ledger 读取和更新逻辑；成功处理或记录 not-needed 后，后续 run 会跳过该 PR。
- 风险：cron 表达式写错导致 workflow 不按小时触发。
  - 缓解：增加测试断言具体 cron 值为 `45 * * * *`，并保留 YAML 字符串引号。
- 风险：误改 prompt 或写入边界导致 scheduled run 影响范围扩大。
  - 缓解：实现时只改 workflow schedule 和对应测试；代码审查确认 prompt、permissions 和 scripts 未变化。

## 7. Testing and validation

- 运行窄测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_docs_sync.py'
```

- 如果实现只改 workflow schedule 和测试，以上测试应覆盖主要行为。若测试 helper 或 shared workflow assumptions 受影响，再运行完整 suite：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

- 运行 diff 检查：

```bash
git diff --check
```

- 人工检查最终 diff，确认 production code、scripts、Codex prompt、ledger schema 和 docs sync write surface 未被修改。

## 8. Follow-ups

- 如果未来每小时一个 PR 仍不足以追上积压，可另开 issue 设计 batch processing；该 follow-up 应重新评估 ledger、PR body 累积和 Codex 成本控制。
- 如果组织内有统一 cron 分钟规范，可在后续调整第 45 分钟，但这不是本 issue 的必需范围。
