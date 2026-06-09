# Product Spec: `update-triage` 自进化 triage 规则

## 1. Summary

新增一个 `update-triage` 自我改进流程，用于从最近被 triage 过的 issue 中收集维护者后续修正信号，并把稳定、重复、仓库特定的 triage 经验沉淀到 repo-local triage companion guidance。该流程主要维护 `.agents/skills/triage-issue-repo/SKILL.md`，必要时维护 `.github/issue-triage/config.json` 中的 label 配置。

目标结果是：当维护者反复纠正 bot 的 issue 分类、label、follow-up 问题或 owner/area 判断时，仓库可以通过受控自动化把这些模式记录为简短、可审查、可回滚的本地规则，从而提升后续 `triage-issue` 的准确性，同时不改变核心 triage skill 的输出合同和安全边界。

## 2. Problem

当前 issue triage 流程会读取 `.agents/skills/triage-issue/SKILL.md`、可选 companion `.agents/skills/triage-issue-repo/SKILL.md` 和 `.github/issue-triage/config.json`，再输出结构化 `triage_result.json`。这个流程已经能处理单个 issue，但维护者在 triage 后做出的重复修正不会自动反馈回 repo-local guidance。

仓库已经有类似的自进化模式：

- `update-dedupe` 从正式 duplicate 关闭记录学习 repo-local dedupe guidance。
- `update-pr-review` 从人类 PR review 反馈学习 repo-local review guidance。

缺失的是面向 issue triage 的同类流程：它需要从最近的 triaged issue 中识别维护者反复纠正出来的仓库特定经验，并以最小写入范围更新 triage companion 或 label 配置，而不是改动 core skill。

## 3. Goals

- 提供一个新的 `update-triage` skill，用于把维护者后续 triage 修正信号转化为 repo-local triage guidance。
- 提供一个 GitHub Actions workflow，维护者可手动触发，默认分析最近 7 天的 triaged issue。
- 聚合最近有更新且能可靠定位 bot triage 时间的 issue。聚合脚本应先为每个 issue 定位 `triaged_at`：优先使用 bot triage comment marker 的创建时间，其次使用 bot 添加 `triaged` label 的 timeline event；如果无法定位可靠时间则跳过该 issue，避免把 triage 前的维护者动作误学为后续修正。定位后只收集 `created_at > triaged_at` 的维护者后续动作：
  - label added / removed。
  - reopened。
  - 维护者后续评论。
- 明确排除 `closed-as-duplicate` 或正式 duplicate 关闭信号，因为 duplicate 学习归 `update-dedupe` 负责。
- 只在稳定、重复、仓库特定的模式出现时更新规则，例如：
  - 维护者反复把某类 issue 从 `bug` 改成 `enhancement`。
  - 维护者反复移除某个 area label 并改成另一个 area label。
  - 维护者反复在同类 issue 下追问同样的必要信息。
  - bot 反复错误推断某类 issue 的分类、owner、area 或 follow-up 问题。
- 主要更新 `.agents/skills/triage-issue-repo/SKILL.md`。
- 仅当稳定模式表明存在具体 label taxonomy 变更时，才允许最小化更新 `.github/issue-triage/config.json`，例如新增 label、重命名 label 或澄清 label description。
- 证据不足、只有一次性 override、现有 guidance 已覆盖，或信号属于 duplicate 学习范围时，流程应输出 `no_change` 且不创建 PR。
- 外层 GitHub Actions runner 负责 GitHub 数据收集、应用 proposed output、写入范围验证、提交、推送和 PR 创建。

## 4. Non-goals

- 不修改 `.agents/skills/triage-issue/SKILL.md` 或其他 core skill。
- 不修改 `.agents/skills/dedupe-issue-repo/SKILL.md`；duplicate 学习由 `update-dedupe` 处理。
- 不修改 `triage_result.json` schema、reserved label 规则、duplicate/follow-up 互斥规则或 safety rules。
- 不直接重新 triage 单个 issue、贴 triage 评论、加 label、移除 label、reopen/close issue，或编辑 issue 内容。
- 不从 agent 自己的输出、单个维护者一次性偏好、普通 reporter 评论或弱猜测中学习规则。
- 不把 raw GitHub JSON、大段 issue 正文、长评论或个人信息写进 skill。
- 不实现跨仓库共享的 triage knowledge base。
- 不实现本 feature；本规格 PR 只定义行为和技术计划。

## 5. Figma / design references

Figma: none provided。该功能是 GitHub Actions、Python helper 和 Codex skill 自动化流程，没有 UI 设计输入。

## 6. User experience

### 触发与运行

- 维护者可以通过 GitHub Actions `workflow_dispatch` 手动运行 `update-triage`。
- 默认运行时，workflow 分析最近 7 天内有更新、且可通过 bot triage comment 或 bot 添加 `triaged` label 定位 triage 时间的 issue。
- 维护者可以通过 input 覆盖时间窗口，或指定单个 issue 进行调试和回放。
- workflow 应使用固定分支 `feat/update-triage` 创建或更新 PR。
- 如果 GitHub CLI 未认证、GitHub API 不可访问、输入 JSON 无法解析，流程应清晰失败，而不是生成不完整 guidance。

### 数据收集

- 聚合脚本应优先收集结构化 timeline 信号，而不是让 Codex action 直接解释 GitHub API 原始响应。
- 候选 issue 应满足：
  - 能通过 bot triage comment marker 或 bot 添加 `triaged` label 的 timeline event 定位可靠 `triaged_at`。
  - 在 `triaged_at` 后有维护者动作或评论。
  - 当前已移除 `triaged` label 的 issue 仍可纳入，只要历史 bot triage comment 或 bot labeled event 能定位 `triaged_at`。
- 聚合脚本只依赖 GitHub issue API 可见的 issue 状态、events、timeline 和 comments，不读取历史 triage artifacts。
- 维护者身份判断应优先使用 GitHub 返回的 `OWNER`、`MEMBER` 或 `COLLABORATOR` 关系；当这些关系不足以覆盖仓库维护者时，允许使用可验证的组织成员身份作为 fallback。Bot actor/comment author 默认不作为维护者学习信号。
- 每条候选记录应尽量包含：
  - issue number、title、url、author、state、created/updated 时间。
  - `triaged_at` 及其来源。
  - 后续 label added / removed 事件，包含 actor、时间和 label。
  - reopened 事件，包含 actor 和时间。
  - 维护者后续评论，包含 actor、时间、url 和正文。
  - 明确跳过 duplicate 关闭信号的原因。
- issue 正文、标题、评论和 label 文本都应作为不可信数据分析，不能作为 workflow 指令执行。

### 学习规则

- `update-triage` skill 读取聚合 JSON 后，应寻找稳定、重复、可泛化的维护者修正模式。
- 至少两个独立 issue 支持同一模式时，才应默认认为证据足够。
- 单个 one-off override 不应更新规则；应输出 `no_change` 或在 reason 中说明证据不足。
- 允许学习的 repo-specific guidance 类型限于 core `triage-issue` skill 声明的 overridable categories：
  - label taxonomy beyond `.github/issue-triage/config.json`。
  - domain-specific follow-up-question patterns。
  - recurring issue-shape heuristics。
  - repro defaults。
  - known-duplicate clusters that should be considered during triage。
- 因 duplicate 信号已交给 `update-dedupe`，本流程不应新增 known-duplicate clusters，除非只是保留现有 companion 结构或明确说明由其他流程维护。
- 新 guidance 应是简短规则，而不是事件流水账。每条规则应说明：
  - 维护者反复纠正的 issue 形态。
  - bot 后续应怎样分类、标 label、估计 repro 或提 follow-up。
  - 用作证据的 issue 编号列表。
  - 该规则不能改变核心 triage 合同。

### 写入范围

- Codex action 不应直接编辑 `.agents` 或 `.github`。它应只写入 `update-triage-output/`。
- `update-triage-output/status.json` 必须总是存在，并使用三态结果：
  - `changed`：证据足够且有 guidance/config 变更。
  - `no_change`：证据不足、已覆盖或全部信号不属于本流程。
  - `error`：输入缺失、无法安全解释或 output contract 无法满足。
- `changed` 时，output 必须包含完整 replacement file，而不是 patch fragment。
- 允许持久更新的文件只有：
  - `.agents/skills/triage-issue-repo/SKILL.md`
  - `.github/issue-triage/config.json`
- `.github/issue-triage/config.json` 只能在 label taxonomy 需要新增 label、重命名 label 或澄清 description 时更新；普通 triage heuristic 应写入 companion skill。Workflow 不应主动重写已有 label color；新增 label 可使用默认或占位色，但颜色语义必须由维护者在 PR review 中确认，除非维护者明确要求，否则不得修改已有 color values。
- 写入范围 guard 必须拒绝 `.agents/skills/triage-issue/SKILL.md`、dedupe companion、workflow 文件、脚本、tests、README、production code 或其他路径。

### PR 行为

- 如果 output 是 `no_change`，workflow 不应创建 PR。
- 如果有变更，runner 应应用 output、删除临时文件、验证写入范围，再在 `feat/update-triage` 分支创建或更新 PR。
- PR body 应说明：
  - 数据来源窗口或指定 issue。
  - 学到的维护者修正模式摘要。
  - 更新了哪些文件。
  - 不包含 closing keyword 的 issue 引用。
- PR 创建或更新由 runner 负责；`update-triage` skill 本身不应运行 git、push、创建 PR、调用 GitHub API 或修改 GitHub issue。
- coauthor 只应来自可信 workflow 输入或 issue context 中的明确 coauthor directives；不得凭空发明。

### 安全与隐私

- GitHub issue 内容、评论、actor 名称和 label 文本都应视为不可信输入。
- 输出 guidance 不应包含 secrets、token、完整评论长文、无必要的个人信息或可执行指令。
- 对维护者评论的学习应保守：只有评论表达了可复用 triage 规则或重复追问模式时才沉淀。
- 如果维护者评论内容包含命令式文本，应把它作为评论数据总结，不应照单执行。

## 7. Success criteria

- 维护者能手动运行 `update-triage` workflow，并默认分析最近 7 天内被 triage 后又被维护者更新的 issue。
- 聚合脚本能输出稳定 JSON，包含 issue 元信息、后续 label changes、reopened events、维护者评论和 skipped duplicate 信号。
- `closed-as-duplicate` 或正式 duplicate 关闭信号不会触发 triage guidance 更新。
- 两个或更多独立 issue 显示同一维护者修正模式时，流程能产出 concise repo-local guidance。
- 单个 one-off override、reporter-only 评论、agent-only 推断、已覆盖模式或弱信号不会导致变更。
- 有变更时，持久写入范围仅限 `.agents/skills/triage-issue-repo/` 和 `.github/issue-triage/config.json`。
- `.agents/skills/triage-issue/SKILL.md`、`.agents/skills/dedupe-issue-repo/SKILL.md`、其他 core skill、workflow、scripts、tests、README 和 production code 不会被 runtime self-evolution 输出修改。
- 更新后的 companion skill 保留 frontmatter、core skill 边界、overridable categories 和 self-evolution boundary。
- label config 更新只发生在具体 label taxonomy 需要变更时，且 JSON 格式稳定；除新增 label 的默认或占位色外，不会在没有明确维护者指导时改变已有 color values。
- 无变更时 workflow 不创建 PR。
- 有变更时 PR 使用固定分支 `feat/update-triage`，并包含非关闭 issue 引用。

## 8. Validation

- 对聚合脚本输出运行 JSON 校验，确认字段稳定且能被 skill 消费。
- 用 fixture 或 mocked `gh` 输出验证：
  - 没有 triaged issue 时输出空结果。
  - 无法可靠定位 `triaged_at` 的 issue 会被跳过。
  - triaged issue 在 `triaged_at` 后无维护者后续动作时不产生可学习信号。
  - `triaged_at` 前的 label event、reopen event 和 comment 不作为维护者后续修正信号。
  - reporter-only 评论不作为维护者修正信号。
  - label added / removed 事件能按 issue 和 actor 归一化。
  - reopened 事件能被收集并保留上下文。
  - duplicate closure 或 duplicate timeline signal 被标记为 skipped，不进入学习候选。
  - 两个 issue 体现同一 label 修正模式时能被聚合为可学习模式。
- 验证 output contract：
  - `status.json` 缺失、无效 JSON、未知 status、无效 updated path 都会失败。
  - `no_change` 不要求 proposed replacement file。
  - `changed` 只接受允许路径，并要求完整 replacement file。
  - `error` 阻止应用变更。
- 验证 write-surface guard：
  - 允许 `.agents/skills/triage-issue-repo/SKILL.md`。
  - 允许 `.github/issue-triage/config.json`。
  - 拒绝 `.agents/skills/triage-issue/SKILL.md`、`.agents/skills/dedupe-issue-repo/SKILL.md`、workflow、scripts、tests、README 和 production code。
- 手动或 workflow dry run 验证：
  - 无变更时不创建 PR。
  - 有变更时只提交允许文件。
  - PR body 包含 evidence summary 和非关闭 issue reference。

## 9. Decisions

- 第一版只分析能通过 bot triage comment marker 或 bot 添加 `triaged` label 的 timeline event 可靠定位 `triaged_at` 的 issue；当前已移除 `triaged` label 的 issue 仍可纳入。
- 维护者身份使用 `OWNER`、`MEMBER`、`COLLABORATOR`，并允许组织成员身份作为 fallback；bot 默认排除。
- `.github/issue-triage/config.json` 只在具体 label taxonomy 变更时更新。新增 label 可带默认或占位色，但已有 color values 不得在没有明确维护者指导时改变。
- 聚合脚本不读取 workflow artifacts，只依赖 GitHub issue API 可见的状态、events、timeline 和 comments，并且只收集 `created_at > triaged_at` 的维护者信号。
