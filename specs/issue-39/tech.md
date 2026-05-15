# 技术规格：实现 `review-spec` 核心技能

## 1. Problem

需要新增一个核心技能 `.agents/skills/review-spec/SKILL.md`，让 Codex 在评审 `specs/` 下文档 PR 时有专门的工作流和评审标准。该技能必须保留现有 PR review 自动化的离线快照、diff line targeting、`review.json` 输出和校验契约，同时把评审判断从代码缺陷转向规格文档质量。

关键技术约束是：当前仓库的 `review-pr` 校验脚本只接受 `body` 和 `comments` 两个顶层字段，因此 issue 正文中展示的 `verdict` 字段不能直接加入实际输出契约，除非另行修改校验脚本。为避免破坏现有自动化，本实现应复用现有契约，不扩展 JSON schema。

## 2. Relevant code

- `.agents/skills/review-pr/SKILL.md` — 现有核心 PR review 技能，定义 `pr_description.txt`、`pr_diff.txt`、`review.json`、severity labels、suggestion block、inline line targeting 和校验工作流。
- `.agents/skills/review-pr/scripts/validate_review_json.py` — 当前唯一 review 输出校验脚本；它只允许 `review.json` 包含 `body` 和 `comments`，并校验 inline comments 是否指向 `pr_diff.txt` 中的 changed `LEFT` 或 `RIGHT` 行。
- `.agents/skills/review-pr-repo/SKILL.md` — 仓库本地代码 PR review wrapper，展示本地 companion 如何引用核心技能且不覆盖核心契约。
- `.agents/skills/review-spec-repo/SKILL.md` — 已存在的 spec-only PR companion，当前只定义仓库本地规格文档评审偏好，不定义核心 schema 或安全规则。
- `.github/workflows/review-pr.yml` — 当前 PR review workflow 固定读取 `.agents/skills/review-pr-repo/SKILL.md`，生成并发布 `review.json`。本次实现不修改该 workflow。
- `.agents/skills/update-pr-review/SKILL.md` — 已把 `.agents/skills/review-spec/SKILL.md` 列为禁止写入的核心技能路径，说明 `review-spec` 应被视为核心契约而非 self-evolution companion。

## 3. Current state

当前系统已有通用代码 PR review 能力：

- workflow 生成 `pr_description.txt` 和 `pr_diff.txt`。
- Codex 按 `.agents/skills/review-pr-repo/SKILL.md` 执行 review。
- `review-pr-repo` 读取并遵循核心 `.agents/skills/review-pr/SKILL.md`。
- `review.json` 由 `.agents/skills/review-pr/scripts/validate_review_json.py` 校验。
- `.github/scripts/post_pr_review.py` 负责把合法 review 结果发布到 GitHub。

当前缺口：

- 没有 `.agents/skills/review-spec/SKILL.md` 核心技能。
- `review-spec-repo` 已存在但只是 companion，没有完整工作流、输出契约和安全边界。
- `update-pr-review` 已将 `.agents/skills/review-spec/SKILL.md` 视作核心 forbidden write surface，但该路径尚不存在。
- Issue 正文中的输出示例包含 `verdict`，但当前校验器会拒绝未知字段；实现时必须解决文档需求与现有 schema 的冲突。

## 4. Proposed changes

### 新增核心技能文件

新增 `.agents/skills/review-spec/SKILL.md`。文件应包含标准 skill frontmatter：

```yaml
---
name: review-spec
description: Review a spec-only GitHub pull request from pinned `pr_diff.txt` and `pr_description.txt` snapshots, then write and validate `review.json` with document-quality findings.
---
```

主体建议结构：

- `# review-spec`
- `## Purpose`
- `## Inputs`
- `## Applicability`
- `## Review Focus`
- `## Out of Scope`
- `## Local Companion`
- `## Inline Comment Rules`
- `## Output`
- `## Workflow`
- `## Final Checks`

### 复用 `review-pr` 契约

`review-spec` 不应复制或改写底层 JSON schema。技能文档应明确：

- 输入仍是 `pr_description.txt` 和 `pr_diff.txt`。
- 输出仍是仓库根目录 `review.json`。
- 输出 shape 与 `review-pr` 当前契约一致：

```json
{
  "body": "Top-level review summary or issues that cannot be attached inline.",
  "comments": []
}
```

- 不加入 `verdict`，因为当前 `validate_review_json.py` 会拒绝未知字段。
- Inline comments 只能定位到 `pr_diff.txt` 中存在的 changed `LEFT` 或 `RIGHT` 行。
- `🧹 [NIT]` 必须包含 GitHub suggestion block。
- suggestion block 只能用于 `RIGHT` 行。

### 文档评审重点

技能应把 issue 中五个核心维度写成可执行规则：

- 完整性：检查是否缺少关键章节、目标、非目标、验收标准、验证计划、开放问题。
- 清晰性：检查需求、术语、约束、状态转换、验收标准是否可被实现代理准确执行。
- 可行性：检查技术方案或计划是否符合仓库现有结构、权限、安全限制和自动化流程。
- 对齐度：检查文档是否忠实反映 issue/PR 范围，避免范围蔓延和遗漏。
- 一致性：检查同一文档内部、产品规格与技术规格之间是否互相矛盾。

技能还应明确只在格式问题影响可读性、可执行性或 reviewer 理解时提出格式评论。

### Scope guard

`review-spec` 应在技能说明中要求先根据 `pr_diff.txt` 判断变更路径是否全部位于 `specs/`。如果发现非 `specs/` 文件：

- 不应进行代码级 review。
- 应在 `review.json.body` 中说明该 PR 不满足 spec-only review 适用范围。
- 仍应输出合法 JSON 并通过校验。

该 guard 是技能行为要求，不需要新增脚本实现。

### 与 `review-spec-repo` 的关系

`review-spec` 应定义核心契约；`.agents/skills/review-spec-repo/SKILL.md` 只作为仓库本地 companion。技能应要求：

1. 先遵循 `.agents/skills/review-spec/SKILL.md` 的核心工作流。
2. 再应用 `.agents/skills/review-spec-repo/SKILL.md` 的仓库本地偏好。

同时写明 `review-spec-repo` 只能补充：

- 仓库要求的必填章节。
- `specs/` 目录下链接规范。
- 仓库特定格式风格。

禁止 companion 覆盖：

- JSON 结构。
- 严重级别标签。
- 安全规则。
- 证据规则。
- suggestion 块格式。
- diff 注解契约。
- 校验脚本要求。

### 不修改 workflow

本 issue 的实现只新增核心技能文件。不要在同一实现中修改 `.github/workflows/review-pr.yml`，因为产品规格把 workflow 路由视为开放后续问题。后续如需让 spec-only PR 自动调用 `review-spec`，应单独设计 workflow 分流。

## 5. End-to-end flow

1. CI 或用户准备好 `pr_description.txt` 和 `pr_diff.txt`。
2. 调用方要求 Codex 读取 `.agents/skills/review-spec/SKILL.md`。
3. Codex 读取 `pr_description.txt`，了解 PR 标题、描述和上下文。
4. Codex 解析 `pr_diff.txt`，建立可评论的 `path/side/line` changed-line 集合，并检查 changed paths 是否都位于 `specs/`。
5. 如果路径不符合 spec-only 范围，Codex 写出合法 `review.json`，在 `body` 中说明范围不匹配，`comments` 可为空。
6. 如果路径符合范围，Codex 按五大文档质量维度评审变更。
7. Codex 只对可精确定位到 changed lines 的问题写 inline comments；跨文档或无法定位的问题写入顶层 `body`。
8. Codex 运行 `python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json`。
9. 如果校验失败，Codex 修复 `review.json` 并重复校验。
10. 最终只留下校验通过的 `review.json`。

## 6. Risks and mitigations

- 风险：issue 示例中的 `verdict` 与当前校验脚本冲突。
  - 缓解：`review-spec` 明确复用 `review-pr` 当前 schema，不添加 `verdict`。如果未来需要 verdict，必须先修改校验脚本和发布脚本。
- 风险：新技能复制 `review-pr` 规则后未来漂移。
  - 缓解：在 `review-spec` 中引用 `review-pr` 的契约和校验脚本，避免定义不兼容的 schema。
- 风险：spec review 对普通代码 PR 输出误导性评论。
  - 缓解：增加 `specs/` path scope guard，并要求非 spec-only PR 使用顶层 `body` 说明范围不匹配。
- 风险：本地 companion 覆盖核心输出契约。
  - 缓解：在核心技能中明确 companion 的允许覆盖范围和禁止覆盖范围。
- 风险：格式类评论噪音过高。
  - 缓解：只允许影响可读性、可执行性或 review 判断的格式问题；minor 格式问题必须有精确 suggestion 才能作为 `🧹 [NIT]`。

## 7. Testing and validation

- 静态检查 `.agents/skills/review-spec/SKILL.md` frontmatter 是否包含 `name: review-spec` 和准确 description。
- 人工比对 `.agents/skills/review-spec/SKILL.md` 与 `.agents/skills/review-pr/SKILL.md`，确认输出 schema、severity labels、suggestion rules 和 validate command 不冲突。
- 人工比对 `.agents/skills/review-spec/SKILL.md` 与 `.agents/skills/review-spec-repo/SKILL.md`，确认 core/companion 边界清楚。
- 准备一个只包含 `specs/example/product.md` changed lines 的 `pr_diff.txt` fixture 和合法 `review.json`，运行：

```bash
python3 .agents/skills/review-pr/scripts/validate_review_json.py pr_diff.txt review.json
```

- 准备一个包含非 `specs/` changed path 的 `pr_diff.txt`，验证技能期望输出为合法 JSON，并在顶层 `body` 描述范围不匹配。
- 不需要新增生产代码测试，因为实现产物是 skill 文档；验证重点是文档契约与现有校验脚本一致。

## 8. Follow-ups

- 后续可设计 workflow 分流：当 PR 只修改 `specs/` 时读取 `review-spec` 或 `review-spec-repo`，其他 PR 继续读取 `review-pr-repo`。
- 后续可考虑新增专用 fixture 或轻量脚本，验证 skill 文档中的示例 `review.json` 与校验脚本兼容。
- 如果维护者确实需要 `verdict` 字段，应另开任务统一修改 `validate_review_json.py`、post review 逻辑、`review-pr` 和 `review-spec` 契约。
