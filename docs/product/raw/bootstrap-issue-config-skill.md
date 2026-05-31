# Issue triage 初始化配置 skill

`bootstrap-issue-config` skill 用于把一个仓库初始化为可被 issue triage agent
稳定识别标签、路径和负责人。它面向首次接入 issue 自动 triage 的仓库，产出长期维护的
triage 配置和 CODEOWNERS-style ownership hints。

## 产出文件

该 skill 生成或更新两个仓库文件：

- `.github/issue-triage/config.json`：triage agent 可使用的 GitHub label 定义。
- `.github/CODEOWNERS`：按路径记录熟悉相关区域的 GitHub 用户，用于 triage、review
  和 owner 推断。

`config.json` 的顶层只包含 `labels` key。`labels` 是以精确 label name 为 key 的平铺对象，
包括 `bug`、`enhancement`、`documentation`、`needs-info`、`duplicate`、`triaged`、
`repro:high`、`repro:medium`、`repro:low`、`repro:unknown` 以及仓库已有或推断出的
area、feature、status labels。每个 label 记录 6 位 hex color 和一句 description。

`.github/CODEOWNERS` 使用 CODEOWNERS 语法；后出现的规则优先。该文件可作为 owner
推断来源。若仓库 branch protection 要求 code owner review，GitHub 可能基于该文件请求
code owner review。

## 初始化行为

skill 会读取仓库现有 labels、最近 issues、issue templates、已有 issue triage config、
已有 CODEOWNERS，以及最近贡献记录来合并生成配置。仓库 labels 很少或不存在时，会 seed
一组基础 feature/status/repro labels，保证 triage agent 有稳定的起点。

初始化是 additive 和幂等的：重复运行不会删除旧 label 配置，不会重复写入已有 CODEOWNERS
行；已有 GitHub label 会跳过，缺失 label 才需要创建。

bootstrap 只负责生成 issue triage config、CODEOWNERS 和必要 labels。仓库本地 companion
skills，例如 `review-pr-repo`、`review-spec-repo`、`triage-issue-repo` 和
`dedupe-issue-repo`，不在 bootstrap 阶段创建空文件；它们应在后续有证据支持的
self-improvement 流程或维护者编辑中按需出现。

来源：PR #118，Issue #117。
