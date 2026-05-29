# Product Spec: Product Docs Sync 每小时调度

## 1. Summary

将 Product Docs Sync workflow 的 scheduled run 从每天一次调整为每小时一次。该 workflow 在自动扫描 merged PR 时，每次只选择一个尚未处理的 PR 交给 docs sync agent；更高频的调度可以降低历史 PR 堆积风险，让 product docs sync ledger 更快追上近期合并记录。

目标结果是：无需维护者手动回放，定时任务每小时自动尝试处理一个未处理的 merged PR；当没有可处理 PR 时保持现有跳过行为；手动 `workflow_dispatch` 能力和已有处理边界不变。

## 2. Problem

当前 Product Docs Sync workflow 每天只在 UTC 02:45 运行一次。由于扫描模式下 context preparation 会从扫描窗口中选择第一个未处理 PR，一次 scheduled run 最多推进一个 PR。如果短时间内合并多个 implementation PR，或 workflow 因外部原因中断，待处理 PR 会以每天最多一个的速度被消化，容易积压。

维护者希望把定时策略改为每小时执行一次，以更符合“一次只处理一个 PR”的实际吞吐能力。

## 3. Goals

- Product Docs Sync 的 scheduled run 每小时触发一次。
- 每次 scheduled run 仍然只处理当前扫描窗口中的第一个未处理 merged PR。
- 没有未处理 PR 时，workflow 仍然清晰跳过并记录 skip reason，不创建无意义 docs sync PR。
- 保留手动触发能力，包括指定 `pr_number`、`scan_days`、`start_date` 和 `end_date`。
- 保留现有 concurrency 行为，避免多个 Product Docs Sync run 同时改写同一 docs sync 分支。
- 保留现有写入边界：agent 只能根据决策更新 `docs/product/`，不能借调度调整扩大写入范围。

## 4. Non-goals

- 不改变 Product Docs Sync 的核心决策逻辑、prompt、ledger schema 或 docs update 判定标准。
- 不改变扫描窗口默认值、PR 排序规则或 “第一个未处理 PR” 的选择策略。
- 不让一次 scheduled run 批量处理多个 PR。
- 不新增 GitHub API 权限、外部服务或第三方依赖。
- 不修改 product docs 内容、spec 以外的长期文档，或任何生产代码。
- 不调整其他 workflow 的 cron 策略。

## 5. Figma / design references

Figma: none provided。该变更是 GitHub Actions 调度行为调整，没有 UI 或交互设计输入。

## 6. User experience

### 定时运行

- GitHub Actions 应每小时触发 `Product Docs Sync` workflow。
- 每次 scheduled run 使用现有默认扫描参数查找 merged PR，并选择尚未记录在 product docs sync ledger 中的第一个 PR。
- 如果找到未处理 PR，workflow 继续准备稳定上下文、运行 docs sync agent、校验结果、更新 ledger，并在需要时创建或更新 Product Docs Sync PR。
- 如果没有未处理 PR，workflow 仍然停止在 “no unprocessed merged pull requests found” 这一类跳过状态，不能因为更高频调度产生空 PR。

### 手动运行

- `workflow_dispatch` 行为保持不变。
- 维护者仍可指定 `pr_number` 处理某个 merged PR。
- 维护者仍可通过 `scan_days` 或 `start_date` / `end_date` 回放某个时间窗口。
- 调度改为每小时不能影响手动运行的输入含义或结果。

### 积压处理

- 当扫描窗口内有多个未处理 PR 时，连续 scheduled run 应按既有排序逐个推进。
- 每个成功完成或明确不需要 docs update 的 PR 都会通过 ledger 记录，后续 scheduled run 不再重复处理该 PR。
- 如果一次 run 正在执行，后续 run 应遵守现有 `product-docs-sync` concurrency group，不并发改写同一分支。

### 安全与边界

- issue、PR、评论、diff 和 docs 内容仍然是不可信输入，只能作为 docs sync 判断的数据。
- 调度频率提高不应放宽 Codex prompt 的写入限制。
- workflow 不应因为每小时运行而自动关闭 issue、修改 unrelated files，或改变 PR 创建策略。

## 7. Success criteria

- `.github/workflows/product-docs-sync.yml` 的 `schedule` cron 表达式表示每小时执行一次。
- `workflow_dispatch` inputs 与现有手动触发能力保持兼容。
- `concurrency.group` 仍为 `product-docs-sync`，且 `cancel-in-progress` 仍不会取消正在进行的 run。
- context preparation 在没有 `pr_number` 时仍只选择一个未处理 PR，而不是批量处理。
- 无未处理 PR 时，workflow 仍输出 skip reason 并停止后续 docs sync 步骤。
- 更高频 scheduled run 不扩大权限、不新增写入目录、不修改 Codex action prompt 的安全边界。
- 自动化测试能覆盖 workflow 同时支持 scheduled 和 manual dispatch，并能验证 scheduled cadence 是 hourly。

## 8. Validation

- 运行针对 Product Docs Sync workflow 的窄测试，确认 schedule 和 manual dispatch 仍存在，且 scheduled cron 是每小时 cadence。
- 运行 Product Docs Sync 相关测试，确认 context selection、ledger skip、write-surface validation 和 PR 创建前置校验不受影响。
- 运行 `git diff --check`，确认 spec 和 metadata 文件没有 whitespace 问题。
- 可选手动检查 GitHub Actions YAML，确认只调整 Product Docs Sync 的 schedule，不影响其他 workflow。

## 9. Open questions

- 每小时运行的具体分钟是否需要固定为当前的 `45` 分，还是可以改为其他分钟以避开组织内其他定时任务。第一版建议保持 `45` 分，只把日频改为小时频。
