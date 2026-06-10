# update-triage 自进化 triage 规则 workflow

`update-triage` workflow 用于从最近被 issue triage 处理过的 issues 中收集维护者后续修正信号，
并把稳定、重复、仓库特定的 triage 经验沉淀到 repo-local triage companion guidance。它不重新
分诊单个 issue，不直接修改 GitHub issues，也不改变 core `triage-issue` skill 的输出合同或安全边界。

## 触发与输入

维护者可以通过 GitHub Actions `Update Triage Guidance` workflow 手动运行该流程。默认运行
分析最近 7 天内有更新、且能可靠定位 bot triage 时间的 issues；workflow inputs 可以覆盖扫描天数，
指定单个 issue 用于调试，并控制是否推送更新分支。

聚合脚本先为每个候选 issue 定位 `triaged_at`：优先使用 bot triage comment marker 的创建时间，
其次使用 bot 添加 `triaged` label 的 timeline event。无法定位可靠 triage 时间的 issue 会被跳过，
避免把 triage 前的维护者动作误学为后续修正。定位后，脚本只收集 `created_at > triaged_at` 的
维护者 label added / removed、reopened 事件和后续评论。

维护者身份优先来自 GitHub 返回的 `OWNER`、`MEMBER` 或 `COLLABORATOR` 关系；必要时可使用可验证
的组织成员身份作为 fallback。显式配置的 maintainer login 是额外维护者来源，不会取代
`OWNER`、`MEMBER`、`COLLABORATOR` 或组织成员 fallback 判定。Bot actor 和普通 reporter
评论默认不作为学习信号。`closed-as-duplicate` 或正式 duplicate 关闭信号由 `update-dedupe`
负责，不进入 triage guidance 学习。

## 规则学习

`update-triage` skill 读取聚合后的 triage feedback JSON，并寻找稳定、重复、可泛化的维护者修正模式。
默认至少需要两个独立 issues 支持同一模式，才认为证据足够。可学习模式包括维护者反复纠正的 label
分类、area 判断、issue shape heuristic、复现度默认值或同类 follow-up question。

证据不足、只有一次性 override、现有 guidance 已覆盖，或全部信号属于 duplicate 学习范围时，流程产出
`no_change`，不修改 repo-local guidance，也不创建无意义更新 PR。证据存在但无法安全解释时，流程应产出
`error`，由外层 workflow 停止应用。

## 写入边界

`update-triage` skill 本身只写临时 `update-triage-output/` 交接目录。需要更新 guidance 时，它输出
完整 replacement file；外层 runner 负责应用输出、校验写入范围、提交、推送以及创建或更新 PR。

持久写入范围仅限：

- `.agents/skills/triage-issue-repo/SKILL.md`
- `.github/issue-triage/config.json`

普通 triage heuristic 应写入 `.agents/skills/triage-issue-repo/SKILL.md`。只有稳定模式表明 label
taxonomy 需要新增 label、重命名 label 或澄清 description 时，才允许最小化更新
`.github/issue-triage/config.json`。流程不得修改 `.agents/skills/triage-issue/SKILL.md`、
`.agents/skills/dedupe-issue-repo/SKILL.md`、workflow 文件、脚本、测试、README 或产品代码。

## PR 行为

有 guidance diff 时，runner 使用固定分支 `feat/update-triage` 创建或更新 PR，并在 PR body 中说明
数据来源窗口或指定 issue、学到的维护者修正模式摘要、更新文件，以及非关闭 issue reference。没有
guidance diff 时，不创建 PR。若实现或后续维护需要更新 `.github/workflows/update-triage.yml` 这类
workflow 文件，推送该类文件仍需要外层 workflow 配置具备 workflow 写权限的 token。

来源：PR #254，Issue #134，`specs/issue-134/product.md`；PR #261。
