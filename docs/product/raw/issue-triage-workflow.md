# Issue triage workflow

Issue triage workflow 用于在 GitHub issue 创建、重新打开、维护者显式请求或手动触发时，
让 Codex agent 产出结构化分诊结果，并由外层 GitHub Actions 负责评论和标签更新。它面向
issue 分诊，不处理 pull request comment，也不把 issue 本文或评论当作可信指令。

## 触发条件

workflow 支持三类入口：

- `issues.opened` 和 `issues.reopened` 会自动触发分诊。
- `issue_comment.created` 只在目标不是 PR、评论作者是 `OWNER`、`MEMBER` 或
  `COLLABORATOR`，且评论正文包含配置的 `@AGENT_LOGIN /triage` 命令时触发。
- `workflow_dispatch` 可由维护者指定 issue number 手动触发。

评论触发会忽略引用块和 fenced code block 中的命令文本。普通讨论、非可信作者评论、未配置
agent login 的评论、PR 评论，以及只 mention agent 但没有 `/triage` 命令的评论，都不是
issue triage 目标。

## 分诊上下文

生成阶段先读取 issue、历史评论、默认分支、`.github/issue-triage/config.json`、
issue templates 和重复检查候选 issues，并写出稳定本地上下文文件供 agent 使用。重复检查候选
由 workflow 预取，包含当前 issue 之外的 open issues，以及最近 7 天内关闭的 closed issues；
pull request items 会被排除。若本次运行来自显式评论触发，该评论会作为 `triggering_comment`
单独传给 agent；历史评论列表会排除这条触发评论，避免同一评论同时作为操作意图和普通讨论上下文。

分诊 agent 必须读取 `triage-issue` 与 `dedupe-issue` skills，并可在存在时读取受限的
repository companion skills。agent 使用 workflow 提供的 `dedupe_candidates.json` 作为重复检查
的权威候选列表，不自行调用 GitHub API 扫描 issues；若候选列表为空，agent 继续完成其余分诊，
并在结果中说明重复检查无法验证。issue bodies、comments、templates、original report 和 fenced
code blocks 都是待分析数据，不是可执行 workflow 指令。

仓库级 `triage-issue-repo` companion skill 只能补充 core `triage-issue` 允许覆盖的类别，
不能重定义分诊输出 schema、安全规则或 follow-up-question contract。该 companion 当前记录的
仓库规则包括：区分观察到的症状与报告者假设；先通过代码检查、文档查询或 web search 自行尝试
回答 follow-up question；只在问题无法由 agent 自行解决且会实质影响分诊置信度时提问；优先提出
具体问题而不是泛泛要求更多信息。label taxonomy 以 `.github/issue-triage/config.json` 为准，
agent 不应自行发明新 labels，除非上层 prompt 明确允许。

## `triage_result.json`

agent 的唯一 handoff 是 `triage_result.json`。该 JSON 包含：

- `labels`：外层 workflow 应同步的、来自 triage config 的 labels。
- `repro`：`high`、`medium`、`low` 或 `unknown`。
- `confidence`：`high`、`medium` 或 `low`。
- `related_files`、`root_cause` 和 `summary`：用于记录证据、可能影响范围和分诊结论。
- `follow_up_questions`：最多 5 个对象，每个对象包含 `question` 和 `reasoning`。
- `duplicate_of`：基于 workflow 提供候选列表识别出的重复 issues；只有 2 个或更多 likely
  duplicates 时才填充。
- `issue_body`：当 workflow 要求评论正文时提供的 markdown summary，否则为空字符串。

`follow_up_questions` 与 `duplicate_of` 互斥。若发现重复 issue，重复判断优先，问题列表必须
为空；若需要 reporter 补充信息，则 `duplicate_of` 必须为空。

`plan-approved`、`ready-to-implement` 和 `ready-to-spec` 是受保护 labels，分诊结果不得请求
添加它们。若配置中存在 `duplicate`，重复结果必须带 `duplicate` 且不能带 `triaged`；若不存在
重复和 follow-up questions，且配置中存在 `triaged`，结果必须带 `triaged`；若存在
follow-up questions，且配置中存在 `needs-info`，结果必须带 `needs-info`。

## GitHub 更新边界

分诊 agent 不直接修改 GitHub。生成阶段只产出并校验 `triage_result.json`，apply 阶段用
写权限 job 再次校验后同步 labels，并在需要时创建或更新带有
`<!-- aicodingflow:triage-issue -->` marker 的 triage comment。

label 同步只管理 triage config 中定义且非受保护的 labels：结果中缺失的已管理 labels 会被移除，
结果中新增的已配置 labels 会被添加；issue 上不属于 managed label set 的其他 labels 会保留。

来源：PR #121，PR #123，PR #133，Issue #19。
