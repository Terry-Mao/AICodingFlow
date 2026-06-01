# Product Spec: Product Docs Sync 跳过不存在的 issue 引用

## 1. Summary

Product Docs Sync 在准备 merged PR 的稳定上下文时，会收集 PR 关联的 issue，并把 issue 内容、评论和相关 specs 提供给后续 docs sync agent。当前当 PR 标题、正文或 `closingIssuesReferences` 中包含不存在的 issue 编号时，上下文准备会失败，导致整个 product docs sync 任务中断。

目标结果是：不存在或无法读取的 issue reference 不应阻止 Product Docs Sync 继续处理目标 PR。系统应跳过这些 missing issue reference，继续生成 PR 上下文、diff、现有产品文档上下文和可读取 issue 的上下文。

## 2. Problem

维护者和 agent 经常在 PR 描述中使用 `Refs #...`、`Fixes #...`、`Closes #...` 等文本引用 issue。引用可能因为拼写错误、issue 被删除、跨仓库编号混淆或权限不可见而不存在。Product Docs Sync 的核心任务是评估已合并 PR 是否需要更新长期产品文档；一个无效 issue 引用不应让整个同步流程失败。

当前失败会造成两个问题：

- docs sync workflow 不能为该 PR 生成上下文和决策。
- ledger 不会记录处理结果，后续 scheduled run 可能重复卡在同一个 PR 上。

## 3. Goals

- 当 PR 引用不存在的 issue 编号时，Product Docs Sync 继续运行。
- 可读取的 linked issue 仍然出现在稳定上下文中。
- 不存在或不可读取的 issue 不出现在 `linked_issues` 列表中。
- 缺失 issue 不阻止读取相关 specs、现有 product docs 或 PR diff。
- 缺失 issue 不改变 Product Docs Sync 对 PR 本身是否可处理的判断。
- 行为可通过单元测试覆盖，避免后续回归。

## 4. Non-goals

- 不修改 issue reference 的提取规则。
- 不支持跨仓库 issue 引用解析。
- 不创建、修复、重命名或关闭任何 GitHub issue。
- 不改变 Product Docs Sync 的 docs update 决策标准、ledger schema、PR 创建策略或 Codex prompt。
- 不把缺失 issue 视为 docs update required。
- 不扩大 workflow 权限或写入范围。

## 5. Figma / design references

Figma: none provided。该变更是 GitHub Actions 自动化脚本的容错行为，没有 UI 或交互设计输入。

## 6. User experience

### 默认行为

- 当 Product Docs Sync 处理一个 merged PR 时，仍然从 PR 的 `closingIssuesReferences`、标题和正文中提取 issue 编号。
- 如果某个 issue 编号可以通过 GitHub API 读取，该 issue 仍然作为 linked issue 写入稳定上下文。
- 如果某个 issue 编号不存在或 GitHub CLI 返回找不到资源的错误，该编号应被跳过。
- 跳过 missing issue 后，workflow 应继续生成：
  - `product-docs-sync-context.json`
  - `product-docs-sync-context.md`
  - `product-docs-sync-diff.md`
  - `product-docs-existing.md`
- 后续 docs sync agent 应收到缺失 issue 之外的全部可用上下文，并继续做 `required`、`uncertain` 或 `not-needed` 决策。

### 混合引用

- 如果 PR 同时引用存在和不存在的 issue，存在的 issue 必须保留。
- 不存在的 issue 不应导致存在 issue 的 specs 被丢失。
- 输出中的 `linked_issues` 只包含成功读取的 issue，不能包含空对象、错误字符串或部分填充的占位数据。

### 全部引用缺失

- 如果 PR 提取出的 issue 编号全部缺失，但 PR 本身可读取且符合处理条件，Product Docs Sync 仍然继续。
- 此时 `linked_issues` 应为空列表，specs 也只应基于可确认存在的 issue 编号读取。
- workflow 不应把“没有可读取 linked issue”当作 `should_run=false`。

### 错误边界

- 只有 issue reference 缺失或不可读取这一类 linked issue fetch 失败应被容错跳过。
- 获取 PR、搜索 merged PR、读取 diff、写上下文文件、解析 ledger 等非 issue-reference 错误仍应按现有失败行为暴露。
- 权限、网络或 GitHub CLI 临时故障可能与 missing issue 表现相似；第一版可保守地只跳过 GitHub CLI 对单个 issue view 的失败，同时通过日志或上下文可见性保留排查空间。

## 7. Success criteria

- PR 正文包含 `Refs #999999` 这类不存在 issue 引用时，Product Docs Sync context preparation 不会中断。
- PR 同时引用存在的 issue 和不存在的 issue 时，生成的 `linked_issues` 只包含存在的 issue。
- `product-docs-sync-context.md` 中只渲染可读取 issue 的详情。
- related specs 只从成功读取或确认可用的 issue 编号对应目录读取，避免因为 missing issue 产生无效 spec 依赖。
- `should_run` 仍由 PR 是否可处理决定，不由 linked issue 是否全部可读取决定。
- 单元测试覆盖 missing issue reference 被跳过且上下文仍写出的场景。

## 8. Validation

- 增加 Product Docs Sync 脚本单元测试，模拟一个 PR 引用存在 issue 和缺失 issue，确认缺失 issue 不会让准备流程失败。
- 增加或更新测试断言，确认输出 payload 中只包含成功读取的 linked issue。
- 运行 Product Docs Sync 相关窄测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_docs_sync.py'
```

- 如果实现触及共享 helper 或 workflow contract，再运行完整测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

- 运行 `git diff --check`。

## 9. Open questions

- 是否需要在 markdown context 或 JSON context 中显式记录 skipped issue 编号，方便维护者排查错误引用。第一版建议只跳过，不新增上下文字段，除非实现阶段发现现有日志不足以定位问题。
