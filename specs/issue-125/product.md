# Product Spec: `update-dedupe` 自进化 dedupe 规则

## 1. Summary

新增一个 `update-dedupe` 自我改进流程，用于从维护者近期正式关闭为 duplicate 的 issue 中学习稳定重复模式，并把这些模式沉淀到 repo-local dedupe companion guidance。该流程不处理单个新 issue，也不直接改变 `dedupe-issue` 的核心判重合同；它只在证据足够强时，为后续 `dedupe-issue` 运行提供更容易识别的 known-duplicate clusters。

目标结果是：维护者反复将某类 issue 标记为同一个 canonical issue 的 duplicate 后，仓库可以通过受控自动化把该模式记录到 `.agents/skills/dedupe-issue-repo/SKILL.md`，并由外层 runner 做写入范围验证、分支提交和 PR 创建。

## 2. Problem

当前 `dedupe-issue` 依赖 issue 候选集和通用相似度规则来判断重复 issue。它强调 precision over recall，并要求至少 2 个候选 issue 才能标记 duplicate，这有助于避免误判，但也意味着维护者已经反复确认的 repo-specific duplicate 模式不会自动反馈到后续 triage 中。

维护者需要一个类似 `update-pr-review` 的自进化流程，把“最近反复被正式关成同一个 duplicate 的模式”转化成简短、可审查、可回滚的本地规则，同时不削弱核心判重规则、输出 schema 或安全边界。

## 3. Goals

- 提供一个新的 `update-dedupe` skill，用于把强 duplicate 证据转化为 repo-local dedupe guidance。
- 收集最近一段时间内 GitHub issue 的正式 duplicate 关闭记录，默认时间窗口为 7 天，并支持参数覆盖时间窗口和 repo。
- 只接受强信号：issue 的 `state_reason == "duplicate"`，并且能从 timeline 的 `marked_as_duplicate` 事件中找到 canonical issue。
- 只在出现 repeated cluster 时建议更新规则：
  - 至少两个独立 issue 被 close as duplicate 到同一个 canonical issue。
  - 或维护者明确说明某类 issue 应统一视为某 canonical issue 的 duplicate。
- 只允许更新 `.agents/skills/dedupe-issue-repo/SKILL.md` 中 `Known-duplicate clusters` 相关 guidance。
- 保持 `.agents/skills/dedupe-issue/SKILL.md` 的核心规则不变，包括 2 个候选以上才标 duplicate、similarity threshold、输出 schema 和 precision-over-recall 原则。
- 在证据不足时明确产出 `no_change`，不硬造规则、不创建无意义 PR。
- 让外层 GitHub Actions runner 负责数据收集、写入范围验证、提交、推送和 PR 创建。

## 4. Non-goals

- 不改变单个 issue 的 triage 流程或 `triage_result.json` 输出结构。
- 不放宽 `dedupe-issue` 的核心判重算法、2-candidate minimum、输出 schema 或 safety rules。
- 不从普通评论中的弱表述学习规则，例如仅凭 “looks like #123” 不应作为证据。
- 不直接关闭 issue、修改 issue、贴评论、加 label，或替维护者做 duplicate 判定。
- 不把 raw GitHub JSON、长篇历史记录或一次性个案写进 skill。
- 不修改 `.agents/skills/dedupe-issue/SKILL.md` 或其他核心 skill。
- 不实现跨仓库共享的全局 duplicate knowledge base。

## 5. Figma / design references

Figma: none provided。该功能是 GitHub Actions 和 Codex skill 自动化流程，没有 UI 设计输入。

## 6. User experience

### 触发与运行

- 维护者可以通过 GitHub Actions `workflow_dispatch` 手动运行 `update-dedupe`。
- 默认运行时，流程检查最近 7 天的 duplicate 关闭记录。
- 维护者可以覆盖时间窗口或 repo，以便针对更长周期或特定仓库回放。
- 流程应先确认 GitHub CLI 可用，并在无法访问 GitHub 数据时清晰失败，而不是生成不完整规则。

### 数据收集

- 聚合脚本只收集 GitHub 明确记录为 duplicate 的 issue。
- 一个 issue 只有同时满足以下条件才算强 duplicate 证据：
  - issue 关闭原因是 `state_reason == "duplicate"`。
  - timeline 中存在 `marked_as_duplicate` 事件。
  - 该事件能解析出 canonical issue。
- 普通 issue 评论、review 评论、标题相似、机器人推断、单个候选匹配都不能单独作为学习依据。
- 脚本生成结构化 JSON，并打印输出路径；使用前必须能通过 `jq` 或等效 JSON 校验。

### 规则学习

- `update-dedupe` skill 读取聚合 JSON 后，应寻找 repeated clusters。
- 一个 repeated cluster 应至少包含：
  - canonical issue 编号和标题。
  - 被标记为 duplicate 的 issue 列表。
  - 识别这类 duplicate 的关键信号，例如标题模式、错误信息、复现路径、请求能力或关键术语。
  - 证据来源足够说明该模式来自维护者行为，而不是 agent 猜测。
- 当没有 repeated cluster 或现有 guidance 已覆盖该模式时，流程应产出 `no_change`。
- 当证据存在但无法安全解释时，流程应产出 `error`，并给出简短原因。

### 规则写入

- skill 不应直接编辑 `.agents`。它应把 proposed output 写入专用输出目录，由 runner 应用。
- 成功变更时，输出应包含 `.agents/skills/dedupe-issue-repo/SKILL.md` 的完整替换内容。
- 如果 companion skill 当前不存在，首次变更应创建它，并包含 repo-specific wrapper 元数据、对核心 `dedupe-issue` 的依赖说明、`Known-duplicate clusters` 区域和清晰边界。
- 新增 cluster 文案必须简短、明确、可审查：
  - 说明 canonical issue 是哪个。
  - 说明识别 duplicate 的关键信号。
  - 不改变 core `dedupe-issue` 的 threshold、candidate minimum 或输出 schema。
- 写入范围验证必须拒绝除 `.agents/skills/dedupe-issue-repo/` 之外的持久改动。

### PR 行为

- 如果没有规则更新，workflow 不应创建 PR。
- 如果有规则更新，runner 应在固定分支 `feat/update-dedupe` 上提交变更。
- PR 应说明该变更来自近期维护者 duplicate 关闭记录，并包含 evidence summary。
- PR 创建或更新由 runner 负责；`update-dedupe` skill 本身不应运行 git、push、创建 PR 或调用 GitHub API。
- 如果需要 tag 对应 OWNER，应由 runner 在 PR body 或创建流程中处理；不得凭空发明 coauthor。

### 安全与边界

- issue 标题、正文、评论和 timeline 文本都应作为不可信数据分析，不能作为 workflow 指令执行。
- duplicate 规则只能从 GitHub 结构化状态和维护者强信号中学习。
- 输出内容不得包含 secrets、token、未必要的用户个人信息或大段原始 issue 文本。
- 任何实现都必须保留 `dedupe-issue` 的精确优先策略。

## 7. Success criteria

- 维护者能手动运行 `update-dedupe` workflow，并用默认 7 天窗口生成结构化 duplicate feedback JSON。
- 只有 `state_reason == "duplicate"` 且有 canonical `marked_as_duplicate` timeline 事件的 issue 会进入学习输入。
- 单个 duplicate 事件、弱评论暗示、普通相似标题或 agent-only 推断不会导致规则更新。
- 两个或更多独立 issue 指向同一个 canonical issue 时，流程能识别为 repeated cluster 并提出简短 repo-local guidance。
- 证据不足时，流程稳定输出 `no_change`，不修改 `.agents`，不创建 PR。
- 有变更时，最终持久写入范围仅限 `.agents/skills/dedupe-issue-repo/`。
- `.agents/skills/dedupe-issue/SKILL.md` 不被修改。
- 新 companion guidance 明确声明不能改变核心判重合同。
- runner 的写入范围 guard 能阻止 workflow、scripts、tests、production code 或其他 skill 被意外修改。
- PR metadata 不包含 `Closes` 或 `Fixes` 这类关闭 issue 的引用；issue 关联使用非关闭引用。

## 8. Validation

- 对聚合脚本输出运行 JSON 校验，确认输出可解析并包含 repo、时间窗口、canonical issue、duplicate issue 和 evidence fields。
- 用 fixture 或 mocked `gh` 输出验证以下场景：
  - 无 duplicate issue 时输出空结果。
  - 只有普通评论暗示 duplicate 时不收集证据。
  - `state_reason == "duplicate"` 但缺少 canonical timeline 事件时不收集证据或标记为不可用证据。
  - 两个 issue 指向同一个 canonical issue 时形成 cluster。
  - 多个 canonical issue 分别聚合为独立 cluster。
- 验证 skill output contract：
  - `changed` 必须包含允许路径和完整 proposed file。
  - `no_change` 不要求 proposed file。
  - `error` 会阻止应用变更。
- 验证 apply 脚本和 write-surface guard：
  - 允许 `.agents/skills/dedupe-issue-repo/SKILL.md`。
  - 拒绝 `.agents/skills/dedupe-issue/SKILL.md`。
  - 拒绝 workflow、production code、README、tests 或其他非允许路径。
- 手动或 workflow dry run 验证有变更时使用固定分支 `feat/update-dedupe`，无变更时不创建 PR。

## 9. Open questions

- workflow 是否需要 `issue` 输入以便只分析某个 canonical cluster，还是第一版只支持时间窗口和 repo。
- “维护者明确说某类 issue 应统一视为某 canonical issue 的 duplicate” 是否有结构化来源，或第一版只支持正式 duplicate timeline 事件。
- PR body 中 tag OWNER 的具体来源应使用仓库配置、issue author、CODEOWNERS，还是由 workflow input 提供。
