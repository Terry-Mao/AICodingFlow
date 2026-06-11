# update-pr-review 自进化 review 规则 workflow

`update-pr-review` workflow 用于从近期人类对 bot PR review 的反馈中学习稳定仓库偏好，并把这些偏好沉淀到 repo-local review companion guidance。它不处理单个 review 请求，不直接发布 review，也不改变 core review skill 的输出合同。

## 触发与输入

维护者可以通过 GitHub Actions `Update PR Review Guidance` workflow 手动运行该流程。默认扫描最近 14 天的反馈；workflow inputs 可以指定扫描天数、单个 PR、需要排除的 agent login，以及是否把非 agent bot 评论作为人类反馈纳入聚合。

聚合后的反馈会交给 `update-pr-review` skill。Agent comments 只能作为上下文，不能单独驱动规则更新；规则学习必须来自 human review comments、human conversation comments 或 human-authored review bodies/comments。

## 规则学习

`update-pr-review` skill 会寻找重复的人类反馈模式或稳定仓库偏好，并按 review type 路由到 repo-local companion skills：

- code review feedback 更新 `.github/skills/review-pr-repo/SKILL.md`。
- spec review feedback 更新 `.github/skills/review-spec-repo/SKILL.md`。

证据不足、没有人类反馈，或现有 guidance 已覆盖该模式时，流程产出 `no_change`，不修改 companion guidance，也不创建无意义更新 PR。证据无法安全解释时，流程应产出错误，由外层 workflow 停止应用。

## 写入边界

`update-pr-review` skill 本身只写临时 `update-pr-review-output/` 交接目录。需要更新 guidance 时，它输出对应 companion skill 的完整 replacement 内容；外层 runner 负责应用输出、校验写入范围、提交、推送以及创建或更新 PR。

持久写入范围仅限 `.github/skills/review-pr-repo/` 和 `.github/skills/review-spec-repo/`。流程不得修改 core review skills、workflow 文件、脚本、测试或产品代码，也不得改变 core review contract，包括输出 schema、severity labels、diff-line targeting、snapshot rules、validation rules 或 safety rules。

## PR 行为

有 guidance diff 时，runner 使用固定分支 `feat/update-pr-review` 创建或更新 PR，并在 PR body 中包含来源输入摘要。创建或更新 PR 时，workflow 只复用同一 head branch 上的 open PR；不会把 closed PR 当作可更新目标。没有 guidance diff 时，不创建 PR。

来源：PR #173。
