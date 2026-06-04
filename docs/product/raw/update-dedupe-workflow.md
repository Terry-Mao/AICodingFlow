# update-dedupe 自进化 dedupe 规则 workflow

`update-dedupe` workflow 用于从维护者近期正式关闭为 duplicate 的 issues 中学习稳定重复模式，
并把这些模式沉淀到 repo-local dedupe companion guidance。它不处理单个新 issue，不直接修改
GitHub issues，也不改变核心 `dedupe-issue` 的判重合同。

## 触发与输入

维护者可以通过 GitHub Actions `Update Dedupe Guidance` workflow 手动运行该流程。默认运行
会检查最近 7 天的 duplicate 关闭记录；workflow inputs 可以覆盖目标 repo、扫描天数，以及是否
真正推送更新分支。

聚合脚本只把强 duplicate 信号作为学习输入：issue 的关闭原因必须是
`state_reason == "duplicate"`，并且 timeline 中必须存在可解析 canonical issue 的
`marked_as_duplicate` 事件。普通评论、标题相似、agent 推断、单个候选匹配或缺少 canonical
timeline 事件的记录都不能单独触发规则学习。

## 规则学习

`update-dedupe` skill 读取聚合后的 duplicate feedback JSON，并只在存在 repeated cluster 时
提出 guidance 更新。Repeated cluster 表示至少两个独立 issues 被维护者关闭为同一个 canonical
issue 的 duplicate，或存在同等强度的维护者结构化证据说明某类 issue 应统一视为同一 canonical
issue 的 duplicate。

证据不足、没有 repeated cluster，或现有 guidance 已覆盖该模式时，流程产出 `no_change`，不
修改 companion guidance，也不创建无意义更新 PR。证据存在但无法安全解释时，流程应产出错误，
由外层 workflow 停止应用。

## 写入边界

`update-dedupe` skill 本身只写临时 `update-dedupe-output/` 交接目录。需要更新 guidance 时，
它输出 `.agents/skills/dedupe-issue-repo/SKILL.md` 的完整 replacement 内容；外层 runner
负责应用输出、校验写入范围、提交、推送以及创建或更新 PR。

持久写入范围仅限 `.agents/skills/dedupe-issue-repo/`。流程不得修改
`.agents/skills/dedupe-issue/SKILL.md`，也不得放宽 2-candidate minimum、similarity
threshold、输出 schema、候选来源或 precision-over-recall 原则。

## PR 行为

有 guidance diff 时，runner 使用固定分支 `feat/update-dedupe` 创建或更新 PR，并在 PR body
中包含 evidence summary。创建或更新 PR 时，workflow 只复用同一 head branch 上的 open PR；
不会把 closed PR 当作可更新目标。没有 guidance diff 时，不创建 PR。若 implementation 分支包含
`.github/workflows/update-dedupe.yml` 这类 workflow 文件变更，仓库需要配置
`WORKFLOW_UPDATE_TOKEN` 以允许外层 workflow 推送该类文件。

来源：PR #129，Issue #125，`specs/issue-125/product.md`；PR #173。
