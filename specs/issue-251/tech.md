# Tech Spec: 跨仓库同步后的 AICodingFlow 测试可移植性修正

## 1. Problem

issue 251 的技术问题是上游模板测试和 companion skill 文案契约在跨仓库同步后不够自包含。产品变更报告的 spec 链接校验逻辑本身是正确的：spec 引用必须解析到仓库内存在的 `specs/issue-<number>/product.md` 或 `tech.md`。但合法链接测试引用了上游仓库才一定存在的 `specs/issue-239/product.md`，使同步仓库在缺少该 fixture 时失败。

第二个问题是 review companion skill 的边界文案被测试锁定，但同步仓库如果没有当前标准文案，就会触发 `test_review_contracts.py` 失败。实现需要修正上游测试和模板文案契约，而不是放宽校验或修改业务代码。

## 2. Relevant code

- `.github/scripts/check_product_change_report_status.py:28` — 提取普通 Markdown inline links。
- `.github/scripts/check_product_change_report_status.py:29` — 识别裸 `specs/issue-*/product.md` 或 `tech.md` 文本。
- `.github/scripts/check_product_change_report_status.py:30` — 限定合法 spec 目标为 `specs/issue-<number>/product.md` 或 `tech.md`。
- `.github/scripts/check_product_change_report_status.py:98` — 从报告路径解析 Markdown link target。
- `.github/scripts/check_product_change_report_status.py:102` — 拒绝外部 URL 和绝对路径。
- `.github/scripts/check_product_change_report_status.py:105` — 相对 `report_path.parent` 解析链接目标。
- `.github/scripts/check_product_change_report_status.py:112` — 将解析结果规范化成 `specs/...` 形式后校验路径 contract。
- `.github/scripts/check_product_change_report_status.py:115` — 要求目标 spec 文件实际存在。
- `.github/scripts/check_product_change_report_status.py:120` — 校验 spec 引用并拒绝裸 spec 路径。
- `.github/aicodingflow-tests/test_product_change_report.py:590` — 合法 spec Markdown 链接测试当前引用 `../specs/issue-239/product.md`。
- `.github/aicodingflow-tests/test_product_change_report.py:608` — 非法 spec Markdown links 测试覆盖不存在文件、外部 URL、非 spec 文件等场景。
- `.github/aicodingflow-tests/test_product_change_report.py:625` — 裸 spec path 必须失败。
- `.github/aicodingflow-tests/test_product_change_report.py:634` — 普通外部链接不应被 spec 校验误伤。
- `.github/aicodingflow-tests/test_review_contracts.py:32` — 断言 repo review companion 不能作为 primary entrypoint。
- `.agents/skills/review-pr-repo/SKILL.md:9` — `review-pr-repo` 当前说明它是 core `review-pr` skill 的 companion。
- `.agents/skills/review-pr-repo/SKILL.md:12` — 当前包含 “Do not invoke this file as the primary review entrypoint” 文案。
- `.agents/skills/review-spec-repo/SKILL.md:9` — `review-spec-repo` 当前说明它是 core `review-spec` skill 的 companion。
- `.agents/skills/review-spec-repo/SKILL.md:12` — 当前包含 “Do not invoke this file as the primary spec review entrypoint” 文案。
- `.github/aicodingflow-tests/AGENTS.md:3` — 明确该测试目录由 AICodingFlow 管理，可能被上游同步覆盖。
- `.github/aicodingflow-tests/AGENTS.md:6` — 禁止把目标项目特有测试放入该目录。

## 3. Current state

Product change report status checker 的主流程已经具备 spec link contract：

1. `validate_report_references()` 调用 `validate_spec_references()`。
2. `validate_spec_references()` 拒绝裸 `specs/issue-*/product.md` 或 `tech.md`。
3. 对 link label 或 target 中明显表示 spec 的 Markdown link，`normalize_spec_link_target()` 从报告文件位置解析相对路径。
4. 解析后的路径必须位于仓库 `specs/` 下。
5. 规范化后的路径必须匹配 `specs/issue-<number>/product.md` 或 `tech.md`。
6. 文件必须存在，否则报错。

这个逻辑满足产品需求，不应为了让同步仓库测试通过而移除 `exists()` 检查。失败源头是测试 fixture 不可移植：上游仓库有 `specs/issue-239/product.md`，其他仓库未必同步历史 specs。

Review contract 测试当前通过字符串断言保护 companion 边界。上游 companion 文件已经包含所需文案，但同步目标如果存在旧版 companion 或 repo-local companion，就可能缺少这些固定短语。实现需要保证模板同步内容和测试契约一致，并把失败解释为 companion 契约缺失，而不是允许 companion 作为主入口。

## 4. Proposed changes

### A. Stabilize product report spec link test fixture

首选实现路径：

- 更新 `.github/aicodingflow-tests/test_product_change_report.py` 的合法 spec 链接用例，使它不依赖 `specs/issue-239/product.md`。
- 合法 fixture 应来自以下两种方式之一：
  - 使用模板保证存在并随测试同步的 `specs/issue-<number>/product.md` 或 `tech.md`；如果选择现有 fixture，需要确认它在同步目标仓库也会存在。
  - 在测试运行期间于临时 repo root 下创建符合 contract 的 spec fixture，例如 `specs/issue-<temporary-number>/product.md`，并在测试结束后由 `TemporaryDirectory` 或显式 cleanup 移除。
- 保持测试报告文件位于 repo root 下的临时目录，确保 relative link 解析路径与真实 workflow 相近。
- 合法链接 target 应由测试根据 `report_path.parent` 和 fixture path 计算，避免硬编码 `../` 层级导致未来移动测试时再次失效。

推荐使用测试内创建 fixture 的方式，因为它完全自包含，不要求目标仓库保留任何历史 issue spec。实现时需要避免污染工作树：

- 使用 `tempfile.TemporaryDirectory(dir=ROOT)` 创建 report 文件。
- 如果 fixture 必须位于 `ROOT / "specs" / "issue-<n>" / "product.md"` 才满足 checker contract，可以选择一个测试专用 issue number，并在 `try/finally` 中删除该文件和空目录。
- 更稳妥的做法是把 fixture 放在已允许写入的临时测试根中之前，先确认 checker 的 `REPO_ROOT` 固定为脚本上两级目录，因此合法 spec 文件必须位于真实 `ROOT/specs` 下。
- 如果创建真实 `ROOT/specs/issue-<n>/product.md`，测试 cleanup 必须删除该临时文件，避免留下未跟踪 spec。

如果维护者希望避免测试写 `ROOT/specs`，替代路径是新增一个上游管理的最小 fixture，例如 `specs/issue-1/product.md`，并确保它作为模板 fixture 同步到目标仓库。但这会增加长期 fixture 文件维护面。

### B. Preserve strict spec link validation

不要修改以下行为，除非测试暴露出真实 bug：

- 外部 URL 或绝对路径 spec link 失败。
- 路径不在 `specs/` 下失败。
- 路径不匹配 `specs/issue-<number>/product.md` 或 `tech.md` 失败。
- 目标文件不存在失败。
- 裸 spec 路径失败。
- 普通 PR URL 或 issue URL 不触发 spec target 校验。

如需调整测试路径，优先改测试 fixture 构造，不改 `check_product_change_report_status.py` 的产品行为。

### C. Stabilize review companion entrypoint contract

确保两个 repo companion skill 都包含测试断言所需的边界短语，并保持含义清楚：

- `.agents/skills/review-pr-repo/SKILL.md` 应包含 “companion to the core”。
- `.agents/skills/review-pr-repo/SKILL.md` 应包含 “Do not invoke this file as the primary”。
- `.agents/skills/review-spec-repo/SKILL.md` 应包含 “companion to the core”。
- `.agents/skills/review-spec-repo/SKILL.md` 应包含 “Do not invoke this file as the primary”。

如果同步目标仓库存在 repo-local companion 内容，更新时应保留其仓库特定规则，只补齐前言边界，不把本地规则删除或迁回 core skill。

### D. Keep write surface narrow

实现 PR 应只修改与该问题直接相关的上游模板文件，预计包括：

- `.github/aicodingflow-tests/test_product_change_report.py`
- `.agents/skills/review-pr-repo/SKILL.md`
- `.agents/skills/review-spec-repo/SKILL.md`
- 如有必要，`.github/aicodingflow-tests/AGENTS.md` 或相关文档契约

不应修改 production code、目标项目业务测试、README 或无关 workflow。只有当实现发现 checker 路径解析本身存在 bug 时，才考虑修改 `.github/scripts/check_product_change_report_status.py`，并必须保持产品 spec 中的严格行为。

## 5. End-to-end flow

1. AICodingFlow 模板同步到目标仓库，包含 `.github/aicodingflow-tests/`、`.github/scripts/` 和 `.agents/skills/`。
2. 目标仓库运行上游管理测试。
3. Product change report 合法 spec link 测试创建或使用同步保证存在的 spec fixture。
4. 测试报告中的 Markdown link 从 report path 解析到该 fixture。
5. `check_product_change_report_status.py` 验证路径 contract 和文件存在性，合法用例返回 `ledger_status == "reported"`。
6. 非法 spec link 用例继续触发 `SystemExit`。
7. Review contract 测试读取两个 repo companion skill，并确认它们只能作为 core review skill 的 companion。
8. 测试通过后，目标仓库不需要修改 `.github/aicodingflow-tests/` 或业务代码来适配上游 fixture。

## 6. Risks and mitigations

- 风险：测试运行时在 `ROOT/specs` 下创建临时 fixture 后 cleanup 失败，留下未跟踪文件。
  - 缓解：使用唯一测试 issue number，`try/finally` 删除文件和空目录；窄测后运行 `git diff --check` 和完整测试时检查无残留。
- 风险：改用已有 fixture 仍然在某些同步仓库缺失。
  - 缓解：优先选择测试自建 fixture，或将最小 fixture 明确纳入模板同步 surface。
- 风险：为了通过测试而放宽 `exists()` 校验，使产品变更报告重新接受错误 spec link。
  - 缓解：非法 link 测试必须继续覆盖不存在 spec 文件，并保持失败断言。
- 风险：companion 文案修复覆盖目标仓库本地规则。
  - 缓解：实现只补齐前言边界短语，保留已有 repo-local review focus 和 self-evolution guidance。
- 风险：`.github/aicodingflow-tests/AGENTS.md` 的边界被误解为禁止修上游测试。
  - 缓解：明确该目录可以在 AICodingFlow 上游修正管理测试，但同步目标不应放入项目特有测试。

## 7. Testing and validation

运行窄测：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_product_change_report.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests -p 'test_review_contracts.py'
```

如果修改 Python 脚本，运行编译检查：

```bash
PYTHONPYCACHEPREFIX=/tmp/aicodingflow-pycache python3 -m py_compile .github/scripts/check_product_change_report_status.py
```

最后运行完整上游管理测试和 whitespace 检查：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/aicodingflow-tests
git diff --check
```

验证时还应人工确认：

- 合法 spec link 测试不再硬编码依赖 `specs/issue-239/product.md`。
- 不存在 spec 文件的非法用例仍失败。
- 两个 review companion skill 都保留 core companion 边界文案。
- `.github/aicodingflow-tests/` 未新增目标项目专属测试。

## 8. Follow-ups

- 可以补充 troubleshooting 文档，说明同步仓库遇到 `.github/aicodingflow-tests/` 失败时应优先回到 AICodingFlow 上游修正模板测试。
- 如果未来更多测试依赖 `specs/issue-*` 历史 fixture，应统一改为自包含 fixture 或明确的模板 fixture。
