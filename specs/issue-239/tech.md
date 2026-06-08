# Tech Spec: Product Change Report spec 链接格式修正

## 1. Problem

产品变更报告生成路径允许引用 specs，但没有定义 spec 链接的规范格式，也没有在报告状态校验中验证 spec 链接目标。`check_product_change_report_status.py` 目前只校验 commit ID 和 related issue URL，因此错误的 spec link 可以进入 `docs/updates/` 并被 ledger 记录为已报告。

技术目标是在报告生成指导和状态校验中建立同一套 spec link contract：从 `docs/updates/auto-update-*.md` 出发，spec 引用必须是指向当前仓库中实际存在 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md` 的仓库相对 Markdown 链接，并通过自动化测试覆盖。

## 2. Relevant code

- `.agents/skills/product-change-report/SKILL.md:56` — 指示 report agent 阅读 `specs/issue-*/product.md` 和 `specs/issue-*/tech.md` 作为 source context。
- `.agents/skills/product-change-report/SKILL.md:79` — 允许报告条目追踪到 PR、issue URL 或 specs，但没有规定 spec 链接格式。
- `.github/workflows/product-change-report.yml:99` — Codex action prompt 要求读取 product-change-report skill。
- `.github/workflows/product-change-report.yml:116` — prompt 允许 “PRs, issue URLs, or specs” source references，但没有提供 spec link 规范。
- `.github/scripts/check_product_change_report_status.py:21` — `COMMIT_ID_PATTERN` 拦截 commit-like tokens。
- `.github/scripts/check_product_change_report_status.py:60` — `linked_issues()` 从 `reportable_prs[].closingIssuesReferences` 收集 linked issue metadata。
- `.github/scripts/check_product_change_report_status.py:76` — `validate_report_references()` 目前只处理 commit ID 和 related issue URL。
- `.github/scripts/check_product_change_report_status.py:127` — `classify_report()` 在报告非空且非 no-change placeholder 后调用 reference validation。
- `.github/aicodingflow-tests/test_product_change_report.py:554` — 已覆盖 related issue 必须使用 issue URL。
- `.github/aicodingflow-tests/test_product_change_report.py:590` — 已覆盖 PR 编号和 linked issue 编号相同时不误判。

## 3. Current state

产品变更报告 workflow 的主要路径是：

1. `.github/scripts/prepare_product_change_report_context.py` 生成 `product-change-report-context.json`、Markdown context 和 diff context。
2. `.github/workflows/product-change-report.yml` 调用 Codex，根据 `.agents/skills/product-change-report/SKILL.md` 生成或更新目标 `docs/updates/auto-update-*.md`。
3. workflow 运行 `.github/scripts/check_product_change_report_status.py` 对报告分类。
4. 如果状态允许，workflow 更新 `docs/updates/.product-change-report-ledger.json` 并按需创建 report PR。

当前校验能力包括：

- 拒绝包含 commit ID 的报告。
- 对 linked issue，如果报告用 “related issue” 一类文字提到 issue 编号但没有包含 metadata 中的 GitHub issue URL，则拒绝。
- 使用 report path 是否有 worktree change 或是否引用当前 PR 来判断 `reported` vs `scanned_no_update`。

缺口是 spec 引用没有任何结构化校验。报告可以写出错误相对路径、外部 URL、目录链接、裸路径或不存在的 spec 文件，状态校验仍可能返回 `reported`。

## 4. Proposed changes

### Spec link contract

在 product report 生成指导中加入明确规则：

- 当报告引用 spec 时，使用 Markdown 链接。
- 链接 target 使用从 `docs/updates/` 报告文件到 `specs/` 的仓库相对路径。
- 对当前报告路径 `docs/updates/auto-update-*.md`，合法示例为：

```markdown
[Product spec](../../specs/issue-239/product.md)
[Tech spec](../../specs/issue-239/tech.md)
```

- 不使用 GitHub blob URL、PR URL、branch URL、裸 `specs/...` 文本或目录链接作为 spec source reference。

可以同时更新 `.agents/skills/product-change-report/SKILL.md` 和 `.github/workflows/product-change-report.yml` 的 Codex prompt。skill 是长期规则来源；workflow prompt 是运行时最靠近 agent 的约束。两者文案应一致，避免后续只读 prompt 或只读 skill 时产生歧义。

### Status checker validation

在 `.github/scripts/check_product_change_report_status.py` 中扩展 `validate_report_references()`，新增 spec link validation helper。建议保持标准库实现，不新增依赖。

建议函数边界：

- `extract_markdown_links(report_text: str) -> list[tuple[str, str]]`
  - 用正则提取普通 Markdown inline links。
  - 不需要完整 Markdown parser；产品报告格式简单，测试覆盖即可。
- `mentions_spec_reference(text: str) -> bool`
  - 判断 link label 或周边文本是否明显表示 spec，例如 `spec`、`product spec`、`tech spec`、`规格`、`技术规格`。
- `normalize_spec_link_target(target: str, report_path: Path) -> Path | None`
  - 拒绝 `http://`、`https://`、anchor-only、empty target。
  - 从 `report_path.parent` 解析相对 target。
  - 归一化后必须位于 repository root 下的 `specs/`。
  - 文件名必须是 `product.md` 或 `tech.md`。
  - 父目录建议匹配 `specs/issue-<number>/`。
- `validate_spec_references(report_text: str, report_path: Path) -> None`
  - 对 spec-like Markdown links 校验 target。
  - 对裸文本中出现 `specs/issue-*/product.md` 或 `specs/issue-*/tech.md` 的情况报错，要求改成 Markdown relative link。

`classify_report()` 已经拥有 `report_path`，但 `validate_report_references()` 当前只接收 `report_text` 和 `context`。实现时可将签名调整为：

```python
def validate_report_references(report_text: str, context: dict[str, Any], report_path: Path) -> None:
    ...
```

然后在 `classify_report()` 中传入 `report_path`。现有测试直接调用 `classify_report()`，通常不需要大面积修改。

### Path resolution details

实现应避免依赖当前工作目录的符号链接状态或 Git 命令：

- 以 `Path.cwd()` 作为 repo root，或用 `report_path` 和当前脚本执行位置推导 root。测试中 `report_path` 可能位于 `ROOT` 下的临时目录；因此更稳妥的是只对链接 target 解析后的路径做 `resolve()`，并检查是否在 `Path.cwd() / "specs"` 下。
- 如果测试需要合法 spec 文件，可在 `TemporaryDirectory(dir=ROOT)` 以外直接使用已有 `specs/issue-*` 文件，或在临时目录中构造 report 但 target 指向真实 repo specs。不要修改现有 specs 作为测试 fixture。
- 使用 `Path.exists()` 校验目标文件存在。

### Tests

在 `.github/aicodingflow-tests/test_product_change_report.py` 的 report status 测试区域增加覆盖：

- 合法 spec link：
  - 创建临时 report 文件。
  - 写入 `[Product spec](../../specs/issue-239/product.md)` 或指向测试可用 spec 文件的等价相对链接。
  - monkeypatch `has_worktree_change` 为 `True`。
  - `classify_report()` 返回 `ledger_status == "reported"`。
- 不存在 spec link：
  - report 写入 `[Product spec](../../specs/issue-999999/product.md)`。
  - 预期 `SystemExit`。
- 外部 spec URL：
  - report 写入 `[Product spec](https://github.com/owner/repo/blob/main/specs/issue-1/product.md)`。
  - 预期 `SystemExit`。
- 裸 spec 路径：
  - report 写入 `Source: specs/issue-239/product.md`。
  - 预期 `SystemExit`。
- 非 spec 文件：
  - report 写入 `[Spec](../../README.md)` 或 `[Spec](../../specs/issue-239/notes.md)`。
  - 预期 `SystemExit`。
- 非 spec 普通链接：
  - report 写入 PR URL 或 issue URL。
  - 保持现有行为，不因普通链接被误判为 spec link。

如果 implementation 同时更新 workflow prompt，应增加或更新 workflow YAML 测试，断言 prompt 包含 spec link 规范，类似当前测试对 commit ID 和 related issue URL 文案的断言。

## 5. End-to-end flow

1. Product change report workflow 准备稳定 context 和 diff context。
2. Codex action 读取 product-change-report skill 和 workflow prompt。
3. 如果报告条目需要引用 spec，agent 写入从 `docs/updates/` 到 `specs/issue-*/product.md` 或 `tech.md` 的 Markdown relative link。
4. workflow 调用 `check_product_change_report_status.py`。
5. status checker 读取报告，先处理 empty/no-change placeholder，再执行 reference validation。
6. validation 拒绝 commit ID、缺少 URL 的 related issue，以及错误 spec link。
7. 只有通过校验的报告才会继续进入 ledger update 和 PR 创建路径。

## 6. Risks and mitigations

- 风险：简单正则 Markdown link parser 漏掉复杂 Markdown 语法。
  - 缓解：产品报告格式简单，优先覆盖 inline links；后续如需支持 reference-style links 可另开 issue。
- 风险：spec-like 文本识别过宽，误伤普通句子。
  - 缓解：只对 Markdown link label/target 或明确 `specs/issue-*/...` 裸路径触发校验；普通描述 “this follows the approved spec” 不应失败。
- 风险：相对路径校验在测试临时目录中不稳定。
  - 缓解：测试使用 repo root 下的 report path 或计算到真实 `specs/` fixture 的相对路径；helper 接收 `report_path` 明确解析起点。
- 风险：历史报告已有错误 spec link，新增校验可能影响重新运行同日期报告。
  - 缓解：第一版不主动迁移历史报告；如果 workflow 重新校验包含错误链接的既有报告，应失败并促使维护者修正该报告，而不是继续记录错误来源。
- 风险：workflow prompt 和 skill 规则不一致。
  - 缓解：使用相同措辞更新两处，并用 workflow prompt 测试锁定运行时约束。

## 7. Testing and validation

运行产品变更报告窄测试：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_change_report.py'
```

如果修改 `.github/scripts/check_product_change_report_status.py`，运行编译检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile .github/scripts/check_product_change_report_status.py
```

如果修改 workflow prompt，确认 YAML 相关测试仍通过，并运行完整 upstream-managed suite：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
```

最后运行：

```bash
git diff --check
```

## 8. Follow-ups

- 如需修复既有 `docs/updates/` 历史报告中的错误 spec 链接，应单独创建 docs cleanup issue，避免与本次 validation contract 混在一起。
- 如果未来产品报告需要支持 Markdown reference-style links 或 GitHub blob URL，可扩展 spec link contract，但需要同时更新生成指导、状态校验和测试。
