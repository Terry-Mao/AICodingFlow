# 产品规格：`review-spec` 文档评审技能

## 1. Summary

新增一个核心 Codex 技能 `review-spec`，专门用于评审 `specs/` 目录下的文档型 PR。该技能应复用 `review-pr` 的离线快照输入与 `review.json` 输出契约，但评审重点从代码缺陷转为规格文档质量，包括完整性、清晰性、可行性、对齐度和一致性。

期望结果是：当 PR 只修改规格文档时，自动化评审能够输出稳定、可验证、可发布到 GitHub 的 `review.json`，并且不会执行 GitHub API、不会修改 PR、不会评审生产代码实现细节。

## 2. Problem

当前仓库已有 `review-pr` 核心技能和 `review-spec-repo` 仓库本地 companion，但缺少一个面向规格文档 PR 的核心 `review-spec` 技能。没有这个核心技能时，规格 PR 容易被普通代码评审规则处理，导致评审关注点偏向代码错误、性能或异常处理，而不是文档是否足以指导后续实现。

该问题会影响两类用户：

- 维护者：需要稳定审查 `specs/` 下产品规格、技术方案和计划文档的质量。
- 自动化代理：需要明确知道如何从 `pr_description.txt`、`pr_diff.txt` 生成只关注规格质量的 `review.json`。

## 3. Goals

- 提供一个新的 `.agents/skills/review-spec/SKILL.md` 核心技能，名称为 `review-spec`。
- 明确该技能只评审 `specs/` 目录下的文档型 PR，包括产品规格、技术方案、计划文档等。
- 保持与 `review-pr` 相同的快照输入模型：读取现有 `pr_description.txt` 和 `pr_diff.txt`，不刷新、不调用 GitHub。
- 保持与 `review-pr` 相同的 `review.json` 输出契约、diff 行定位规则、严重级别标签、suggestion 规则和校验流程。
- 将评审重点限定在规格文档质量：完整性、清晰性、可行性、与 issue/PR 意图的对齐度、文档内部一致性。
- 明确禁止代码级评审范围，例如不针对生产代码的错误处理、性能优化或实现风格提出评论。
- 说明如何结合 `.agents/skills/review-spec-repo/SKILL.md` 的仓库本地规则，并限制本地规则只能补充仓库特定章节、链接和格式要求。
- 确保该技能的最终产物仅为 `review.json`。

## 4. Non-goals

- 不实现或修改规格评审运行的 GitHub Actions workflow。
- 不修改 `.agents/skills/review-pr/SKILL.md` 的核心评审契约或校验脚本。
- 不修改 `.agents/skills/review-spec-repo/SKILL.md`，除非后续独立任务要求。
- 不新增发布评论、拉取 live PR 状态、生成 diff 快照或调用 `gh` 的能力。
- 不把 `review-spec` 扩展为代码 PR 的通用评审技能。
- 不要求在本次规格工作中实现 feature；本 PR 只产出规格文档和 PR metadata。

## 5. Figma / design references

Figma: none provided。该需求是仓库自动化技能与文档工作流变更，不涉及 UI 或视觉设计。

## 6. User experience

### 默认工作流

- 用户或 CI 在规格文档 PR 场景下触发 `review-spec`。
- 工作区中已经存在 `pr_description.txt` 和 `pr_diff.txt`。
- `review-spec` 读取这两个快照文件，把它们视为唯一 PR 来源。
- `review-spec` 分析变更是否属于 `specs/` 下的文档型内容，并按文档质量维度选择 findings。
- `review-spec` 写入仓库根目录 `review.json`。
- `review-spec` 运行既有校验脚本，直到 `review.json` 满足输出契约。
- 最终不输出其他持久化文件，不调用 GitHub API，不修改源文档。

### 评审范围

- 只评审 `specs/` 目录下的文档 PR。
- 关注产品规格、技术方案、计划文档等是否足以支撑实现和评审。
- 如果 diff 包含非 `specs/` 文件，技能应将其视为不符合规格 PR 适用范围，并在顶层 `body` 中说明无法按 spec-only 规则完整评审，除非后续 workflow 已在调用前保证只传入 specs diff。
- 对文档格式只在影响可读性、可执行性或 review 可用性时提出意见。
- 不因为个人写作偏好、轻微措辞、无影响的排版差异提出评论。

### 五大核心维度

- 完整性：文档是否覆盖 issue 或 PR 描述中的全部关键范围，是否包含必要目标、非目标、验收标准、验证方式和开放问题。
- 清晰性：需求、约束、流程、验收标准是否无歧义，实施代理能否按文档行动。
- 可行性：技术方案是否能在现有仓库结构和自动化约束下落地，是否存在明显不可执行的步骤。
- 对齐度：文档是否忠实对应 issue 或 PR 意图，没有范围蔓延、遗漏或引入未讨论的大型变更。
- 一致性：同一文档内以及产品规格与技术方案之间是否没有互相矛盾的要求。

### 评论行为

- 所有 inline comments 必须以 `review-pr` 已定义的严重级别标签开头：
  - `🚨 [CRITICAL]`
  - `⚠️ [IMPORTANT]`
  - `💡 [SUGGESTION]`
  - `🧹 [NIT]`
- 严重缺失、矛盾或会导致后续实现失败的问题使用 `🚨 [CRITICAL]`。
- 缺失关键细节、歧义、可行性问题使用 `⚠️ [IMPORTANT]`。
- 结构或清晰度优化使用 `💡 [SUGGESTION]`。
- minor 措辞或格式问题只有在可提供精确 suggestion 时才使用 `🧹 [NIT]`。
- 没有明确 diff 行可定位的问题放入顶层 `body`，不要强行贴到无关行。
- Diff 注解规则与 `review-pr` 保持一致：
  - `[OLD:n]` 对应 `LEFT`。
  - `[NEW:n]` 对应 `RIGHT`。
  - `[OLD:n,NEW:m]` 对应 `RIGHT` 的 `m`。
  - 无明确注解的问题进入顶层 `body`。

### 与本地 companion 的关系

- `review-spec` 是核心技能，定义通用工作流、输出契约、安全边界和文档质量评审重点。
- `.agents/skills/review-spec-repo/SKILL.md` 只能补充仓库本地偏好。
- 本地 companion 可以覆盖或补充的内容仅限：
  - 仓库要求的必填章节。
  - `specs/` 目录下链接规范。
  - 仓库特定格式风格。
- 本地 companion 不能覆盖 JSON 结构、严重级别、安全规则、证据规则、suggestion 块格式或 diff 注解契约。

## 7. Success criteria

- 仓库中存在新的 `.agents/skills/review-spec/SKILL.md`，frontmatter 中 `name` 为 `review-spec`，description 清楚说明它用于从 `pr_diff.txt` 和 `pr_description.txt` 评审 spec-only PR 并写入 `review.json`。
- 技能文档明确列出输入文件、输出文件和禁止行为：不调用 `gh`、不发布 GitHub 评论、不重新生成快照、不修改 specs 文档。
- 技能文档明确复用 `review-pr` 的 `review.json` shape、inline target 规则、severity labels、suggestion block 规则和 `validate_review_json.py` 校验步骤。
- 技能文档明确它只关注文档质量，不做生产代码级评审。
- 技能文档包含 issue 中给出的五个核心评审维度，并把它们转换为可执行的评审规则。
- 技能文档明确说明 `review-spec-repo` 的允许覆盖范围和禁止覆盖范围。
- 技能文档包含最终检查步骤：运行 `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`。
- 当没有可定位 inline findings 时，`review.json` 仍然使用合法 JSON，`comments` 为 `[]`，广泛问题写入 `body`。
- 文档不会要求新增或修改 GitHub Actions，也不会要求修改生产代码。

## 8. Validation

- 人工检查 `.agents/skills/review-spec/SKILL.md` 是否覆盖 issue 中的定位、五大维度、必须做、本地覆盖规则、diff 注解规则、评论标签、输出格式和最终检查。
- 人工检查该技能是否与 `.agents/skills/review-pr/SKILL.md` 的输出契约保持一致，没有引入不兼容的 JSON 字段。
- 人工检查该技能是否与 `.agents/skills/review-spec-repo/SKILL.md` 的 companion 边界一致。
- 使用一个示例 `pr_diff.txt` 和 `review.json` 运行 `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`，确认校验流程仍可复用。
- 对包含非 `specs/` 文件的输入进行人工或测试验证，确认技能不会假装完成 spec-only review，而是在顶层 `body` 说明范围不匹配。

## 9. Open questions

- 是否需要后续单独更新 `.github/workflows/review-pr.yml`，在 spec-only PR 中调用 `review-spec` 而不是 `review-pr-repo`？本规格将该 workflow 改动视为非目标。
- 是否需要提供 fixture 示例来验证 `review-spec` 的典型 approve/reject 输出？当前需求未强制要求。
- `review.json` 是否应包含 issue 正文示例中的 `verdict` 字段？现有 `review-pr` 校验脚本不接受 `verdict`，因此本规格以当前仓库契约为准，不新增该字段。
