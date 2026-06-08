# Product Spec: 跨仓库同步后的 AICodingFlow 测试可移植性修正

## 1. Summary

AICodingFlow 的 `.github/aicodingflow-tests/` 是上游模板管理的测试套件，会同步到使用该模板的其他仓库。issue 251 反映同步后运行测试时出现失败：一个产品变更报告 spec 链接测试引用了当前上游仓库才存在的 `specs/issue-239/product.md` fixture；同时 repo review companion skill 的入口边界文案断言在目标仓库中不稳定，导致 Codex 试图直接修改同步下来的测试或 companion 文案来让目标仓库通过。

期望结果是：上游管理测试在同步到其他仓库后仍然可运行、可解释，并且失败时不会诱导 agent 修改目标项目业务代码或私自改写 `.github/aicodingflow-tests/`。产品变更报告的 spec 链接存在性校验继续保持严格，但测试 fixture 必须随测试自身稳定存在或使用仓库内 guaranteed fixture。review companion skill 的边界文案必须成为明确模板契约，让同步仓库能通过相同断言。

## 2. Problem

当前失败不是目标仓库业务逻辑问题，而是 AICodingFlow 上游模板的可移植性问题：

- `test_product_change_report.py` 的合法 spec 链接用例引用 `../specs/issue-239/product.md`。
- `check_product_change_report_status.py` 按设计要求 spec 链接解析后位于 `specs/issue-<number>/product.md` 或 `tech.md`，并且目标文件必须存在。
- 上游 AICodingFlow 仓库有 `specs/issue-239/product.md`，所以窄测在本仓库通过；同步到没有该 fixture 的目标仓库后失败。
- `test_review_contracts.py` 断言 `.agents/skills/review-pr-repo/SKILL.md` 和 `.agents/skills/review-spec-repo/SKILL.md` 必须包含 repo companion 边界文案；目标仓库如果没有同步到当前约定文案，也会失败。
- `.github/aicodingflow-tests/AGENTS.md` 已说明该目录由 AICodingFlow 管理，可能被后续同步覆盖，不应放目标项目特有测试。

这些失败会让 agent 误以为应该在目标仓库中临时修改测试、换 fixture 或补 companion 文案。实际需要在上游模板中定义稳定契约，让同步行为本身可靠。

## 3. Goals

- 让 `.github/aicodingflow-tests/` 中的产品变更报告 spec 链接测试不依赖某个目标仓库可能缺失的历史 issue spec fixture。
- 保持 spec 链接校验的产品行为不回退：引用 spec 时仍必须是 Markdown 链接、路径合法、位于 `specs/issue-<number>/product.md` 或 `tech.md`，且目标文件存在。
- 明确 review companion skill 是 core review skill 的补充文件，不能作为 primary entrypoint 使用。
- 让 `review-pr-repo` 与 `review-spec-repo` 的入口边界文案在上游模板和同步仓库中稳定满足测试断言。
- 保留 `.github/aicodingflow-tests/` 作为上游管理测试的边界：目标项目不应把业务特有测试放入该目录。
- 降低 agent 遇到同步失败时修改错误位置的概率，失败信息和测试 fixture 应指向上游可维护的模板契约。

## 4. Non-goals

- 不放宽 `check_product_change_report_status.py` 对 spec 链接存在性的校验。
- 不允许产品变更报告使用不存在的 spec 文件、外部 spec URL、裸 `specs/...` 文本或非 `product.md` / `tech.md` 文件作为合法 spec 引用。
- 不为每个同步目标仓库创建 issue 239 fixture，也不要求目标仓库保留上游历史 specs。
- 不把 `.github/aicodingflow-tests/` 改成目标项目自定义测试目录。
- 不实现 feature、修复代码或修改 workflow；本 PR 仅产出 issue 251 的产品与技术规格。
- 不改变 review core skill、security review skill 或 shared review schema 的职责。

## 5. Figma / design references

Figma: none provided。该变更是 GitHub Actions、上游测试和 Codex skill 文档契约的行为修正，没有 UI 或视觉设计输入。

## 6. User experience

### 同步仓库维护者体验

- 维护者将 AICodingFlow 模板同步到其他仓库后，可以运行 `.github/aicodingflow-tests/` 中的测试，而不需要先补齐上游历史 issue specs。
- 如果产品变更报告 spec 链接测试失败，失败应代表真正的链接校验回退，而不是缺少某个上游专属 fixture。
- 维护者不需要在目标仓库中修改 `.github/aicodingflow-tests/` 来适配本地业务结构；该目录的测试应保持模板级、可同步。
- 如果目标仓库需要自己的测试，应继续放在目标项目自己的测试结构中，或需要 `.github` 下测试时使用 `.github/tests/`。

### Agent 行为体验

- Agent 看到 product report spec 链接测试失败时，应判断是上游测试 fixture 或模板契约问题，而不是直接放宽 spec 链接校验。
- Agent 不应通过把合法用例改成某个碰巧存在的目标仓库 spec 来掩盖可移植性问题，除非该 fixture 是模板保证存在并随测试同步的 fixture。
- Agent 看到 repo review companion 文案测试失败时，应补齐 companion 的边界契约文案，而不是把 companion 文件当成 primary review workflow。
- Agent 应尊重 `.github/aicodingflow-tests/AGENTS.md`：不要把目标项目专属测试加入该目录，也不要把该目录当作目标仓库长期自定义测试 surface。

### 产品变更报告 spec 链接行为

- 合法 spec 链接用例必须继续证明：Markdown 链接 target 能从报告文件位置解析到仓库内真实存在的 `specs/issue-<number>/product.md` 或 `specs/issue-<number>/tech.md`。
- 测试可以引用上游模板中 guaranteed 存在的 spec fixture，或在测试运行时创建临时但符合 contract 的 fixture。
- 不存在的 spec 文件链接必须继续被拒绝。
- 外部 URL spec 链接必须继续被拒绝。
- 裸 `specs/issue-*/product.md` 或 `tech.md` 文本必须继续被拒绝。
- 普通 PR URL 或 issue URL 链接不应因为不是 spec 链接而被误判。

### Review companion 边界行为

- `.agents/skills/review-pr-repo/SKILL.md` 必须清楚说明它是 core `review-pr` skill 的 companion。
- `.agents/skills/review-spec-repo/SKILL.md` 必须清楚说明它是 core `review-spec` skill 的 companion。
- 两个 companion 都必须包含禁止作为 primary entrypoint 调用的文案。
- Companion 可添加仓库特定偏好和检查重点，但不能覆盖 core workflow、shared review contract、output schema、severity labels、diff-line targeting、validation rules 或 safety rules。

## 7. Success criteria

- 产品变更报告合法 spec 链接测试不再依赖同步目标仓库可能没有的 `specs/issue-239/product.md` fixture，或该 fixture 被替换为随模板稳定存在的 fixture。
- `check_product_change_report_status.py` 对 spec 链接的严格校验行为保持不变或更明确；不存在文件、错误路径、外部 URL 和裸路径仍失败。
- `.github/aicodingflow-tests/test_product_change_report.py` 中的合法链接测试在没有上游历史 issue 239 spec 的同步仓库中也能通过。
- `.github/aicodingflow-tests/test_review_contracts.py` 能稳定验证两个 repo companion skill 都包含 “companion to the core” 与 “Do not invoke this file as the primary” 的边界文案。
- `.github/aicodingflow-tests/AGENTS.md` 的管理边界保持有效，implementation 不把目标项目特有测试加入该目录。
- 修复范围限于上游模板的测试 fixture、测试用例、companion skill 文案或直接相关的文档契约；不修改目标仓库业务代码。

## 8. Validation

- 运行产品变更报告窄测试，确认合法 spec 链接和非法 spec 链接用例都符合预期。
- 运行 review contract 窄测试，确认 core/security review skill 合同引用和 repo companion 边界文案都符合断言。
- 如修改 Python 脚本，运行对应 `py_compile`。
- 运行完整 `.github/aicodingflow-tests/` 套件，确认上游管理测试作为模板整体仍通过。
- 运行 `git diff --check`，确认 Markdown、skill 和测试文件没有 whitespace 问题。

## 9. Open questions

- 合法 spec 链接测试应优先使用已有 `specs/issue-1/product.md` 这类 guaranteed fixture，还是在测试临时目录中创建符合 `specs/issue-<number>/product.md` contract 的 fixture？第一版建议选择最小、最稳定且不会暗示目标仓库必须保留上游历史 specs 的方案。
- 是否需要把 `.github/aicodingflow-tests/AGENTS.md` 的边界说明同步补充到 troubleshooting 文档？第一版可先通过测试和 skill 文案稳定契约，文档扩展作为 follow-up。
