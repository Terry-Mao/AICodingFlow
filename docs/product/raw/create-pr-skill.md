# Create PR skill

`create-pr` skill 用于从当前已提交并已推送或可推送的工作分支创建 review-ready
GitHub pull request，或更新当前分支上仍然 open 的既有 PR。它负责准备 PR
标题、正文、base/head 信息和 issue 关联，不负责实现代码、提交、推送分支或修改
GitHub issue。

## 创建与更新规则

创建或更新 PR 时，skill 只复用当前 head branch 上仍处于 open 状态的 PR。检查现有
PR 时应按当前分支和 `open` 状态过滤；已 merged 或 closed 的历史 PR 不可复用，也不应阻止
同名分支创建新的 PR。

如果找到当前分支的 open PR，skill 会更新该 PR，而不是创建重复 PR。更新前需要读取既有
PR body，并保留不明显属于本 workflow 生成内容的人工补充，例如手写 notes、review context、
checklist 或 release details。

如果没有当前分支的 open PR，skill 会创建新 PR。即使同名分支过去已经有 merged 或 closed
PR，也应视为没有可更新的现存 PR。

来源：PR #191，Issue #178。
