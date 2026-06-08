# Product Spec: Product Change Report spec 链接格式修正

## 1. Summary

产品变更报告可以在条目中引用相关 spec，帮助维护者从 `docs/updates/` 回溯到已批准的产品规格或技术规格。当前 issue 指出 “product report 中 spec 链接地址不对”：报告生成提示和产品报告状态校验没有定义 spec 链接的稳定格式，因此生成报告可能写入不可点击、指向错误分支、指向错误仓库位置，或与仓库路径不一致的 spec 链接。

目标结果是：产品变更报告引用 spec 时使用稳定、可验证的仓库相对 Markdown 链接；错误的 spec 链接不能通过产品报告状态校验；不引用 spec 的有效报告不受影响。

## 2. Problem

`product-change-report` workflow 明确允许报告 “Include source references to PRs, issue URLs, or specs where useful”，但没有说明 spec 应如何链接。现有状态校验只拦截 commit ID 和缺少 URL 的 related issue 引用，不校验 spec 引用是否存在、是否在 `specs/` 下、是否使用正确 Markdown target。

这会导致两个问题：

- 维护者阅读报告时无法可靠从报告跳转到对应 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md`。
- 错误链接一旦进入 `docs/updates/`，ledger 可能把该 merged PR 记为已报告，后续自动报告不再自然修正该条目。

## 3. Goals

- 为产品变更报告中的 spec 引用定义稳定格式。
- 允许报告引用仓库中实际存在的 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md`。
- 禁止或拒绝明显错误的 spec 链接，例如不存在的 spec 路径、脱离 `specs/` 的路径、指向 `docs/updates/` 自身的路径、裸 `specs/...` 文本但不是 Markdown 链接 target。
- 保持现有 PR、issue URL 和 commit ID 校验语义不回退。
- 保持产品变更报告仍然只记录已合并、可验证的变化，不把计划中或未合并 spec 描述为已交付。
- 为该行为增加自动化测试，防止错误 spec 链接再次通过。

## 4. Non-goals

- 不改变产品变更报告的扫描窗口、PR 排序、ledger schema 或 PR 创建策略。
- 不改变报告是否 reportable 的核心判断标准。
- 不要求每个报告条目都必须引用 spec；只有在报告选择引用 spec 时才校验格式和目标。
- 不修改已存在的 `docs/updates/` 历史报告，除非后续 implementation 明确需要单独迁移。
- 不新增外部链接解析服务、GitHub API 调用或第三方依赖。
- 不修改 production code、长期 product docs、compiled wiki，或 unrelated workflow。

## 5. Figma / design references

Figma: none provided。该变更是 GitHub Actions 自动生成 Markdown 报告的链接规范和校验行为修正，没有 UI 设计输入。

## 6. User experience

### 报告生成

- 当产品变更报告引用 spec 时，报告条目应使用 Markdown 链接，target 为仓库相对路径。
- 合法 spec 链接 target 只应指向当前仓库中的 checked-in spec 文件，例如：
  - `[Product spec](../../specs/issue-239/product.md)`
  - `[Tech spec](../../specs/issue-239/tech.md)`
- 从 `docs/updates/auto-update-*.md` 出发，spec 链接应能在 GitHub Markdown 中跳转到对应 spec 文件。
- 报告可以同时引用 PR、GitHub issue URL 和 spec；这些引用应互不替代。
- 如果可用上下文中没有相关 spec，报告仍可只引用 PR 或 issue URL。

### 错误链接处理

- 如果报告文本出现 Markdown 链接且链接文字或目标明显表示 spec，但 target 不是合法 spec 路径，产品报告状态校验应失败，而不是把报告标记为 `reported`。
- 如果 report text 使用 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md` 的裸文本来表达 spec 引用，应该被视为不符合链接规范；维护者需要能看出这是需要修正的报告输出。
- 指向不存在文件的 spec 链接应被拒绝。
- 指向 `specs/issue-*/` 目录但不是具体 `product.md` 或 `tech.md` 文件的链接应被拒绝。
- 指向外部 URL 的 spec 链接应被拒绝，避免报告链接到易漂移的 branch、PR preview 或非仓库 source of truth。

### 不受影响的行为

- 不包含 spec 引用的有效产品变更报告仍按现有规则处理。
- PR 引用仍可用 PR URL、`PR #N` 或 `#N` 形式被识别。
- Related issue 引用仍必须使用 linked issue metadata 中的 GitHub issue URL。
- Commit-like SHA token 仍必须被拒绝。
- 空报告或完整 “no changes” 占位报告的处理不变。

## 7. Success criteria

- `product-change-report` skill 或 workflow prompt 明确要求 spec source reference 使用仓库相对 Markdown 链接，并给出 `docs/updates/` 到 `specs/` 的正确相对路径格式。
- 产品报告状态校验会接受存在的合法 spec Markdown 链接。
- 产品报告状态校验会拒绝不存在的 spec 文件链接。
- 产品报告状态校验会拒绝外部 URL spec 链接。
- 产品报告状态校验会拒绝裸 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md` 文本作为 spec 引用。
- 产品报告状态校验会拒绝指向非 `product.md` / `tech.md` 的 spec 路径。
- 现有 commit ID、related issue URL、PR reference、empty/no-change report 测试保持通过。
- 实现只修改与产品变更报告 spec 链接规范直接相关的 skill、workflow prompt、状态校验脚本和测试；不修改 README、production code 或 unrelated workflow/script/test 文件。

## 8. Validation

- 针对产品变更报告运行窄测试，覆盖合法 spec 链接和错误 spec 链接。
- 运行产品变更报告相关测试，确认原有报告状态分类行为不回退。
- 运行 Python compile 或单元测试验证新增校验逻辑没有语法错误。
- 运行 `git diff --check`，确认新增或修改的 Markdown 与 Python 文件没有 whitespace 问题。
- 人工检查一份示例 `docs/updates/auto-update-*.md` 中的 spec 链接，从报告路径出发应能跳转到目标 `specs/issue-*/product.md` 或 `tech.md`。

## 9. Open questions

- 是否需要迁移或修复既有 `docs/updates/` 历史报告中的错误 spec 链接？第一版建议不做历史迁移，只防止新报告继续生成错误链接。
- 是否允许 spec 链接仅指向 `product.md`，还是 `tech.md` 也应作为同等合法 source reference？第一版建议两者都允许，因为产品报告可能需要引用行为规格或实现风险说明。
