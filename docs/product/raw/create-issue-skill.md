# Create issue skill

`create-issue` skill 用于把用户请求、显式 issue 文本或当前对话上下文转成 GitHub issue。它是本地开发流的入口能力：先创建可分诊、可审查的问题，再进入分支、提交、推送和 PR 流程。

## 模板选择与 issue 内容

Skill 会从目标仓库读取 GitHub issue 模板，包括根目录 `.github/ISSUE_TEMPLATE.md` 以及 `.github/ISSUE_TEMPLATE/` 下的 markdown 和 YAML issue forms。`.github/ISSUE_TEMPLATE/config.yml` 或 `config.yaml` 只用于判断 blank issue 是否禁用、是否存在外部联系方式；contact links 不视为 issue 模板。

模板选择基于用户请求和模板元数据，例如文件名、名称、描述、默认标题、labels 和表单字段。常见分类包括 bug、enhancement、documentation、question/support 和 security。若多个模板同样匹配且会改变必填字段或 metadata，agent 需要先向用户确认；若没有模板适配且 blank issue 未禁用，则创建简洁 plain issue。

Issue 标题和正文只能使用用户请求、附件或当前对话中支持的事实。Markdown 模板会保留有用标题和必填字段，移除作者提示性占位说明；未知必填字段使用 `Not provided`。YAML issue forms 会转换成 markdown body 供 GitHub CLI 创建。Skill 不得虚构版本、日志、labels、assignees、milestones、日期、优先级或环境信息。

## Metadata 与创建边界

`create-issue` 默认不添加分类 labels；有自动 triage 的仓库由后续 issue triage workflow 负责分类、复现度和重复检测。只有用户显式要求，或模板需要明确的非分类 routing label 时，skill 才传递 label。Assignees、milestones 和 projects 也只在用户显式要求或模板明确要求时设置。

创建 GitHub issue 是外部副作用。若用户明确要求创建 issue，且 repository、模板或 plain fallback、标题、正文和 metadata 都明确，skill 可以直接创建。否则需要展示紧凑预览并等待确认。用户只要求 draft、prepare 或 write issue 时，也需要先确认。

创建时使用 `gh issue create`，并把 repository、title、body file 和 metadata 作为独立 argv 参数传递。正文优先写入临时 body file，避免把用户或对话派生内容直接拼进 shell command。若 `gh` 不可用、未认证或无权限，skill 不使用 `gh api` 或 raw HTTP fallback，只报告可供手动创建的 repository、标题、正文和显式 metadata。

## 安全报告处理

如果请求涉及漏洞、exploit、secret 暴露、credential 泄露、私有客户数据暴露或类似敏感安全问题，`create-issue` 默认不得创建公开 issue。Skill 应先查找 GitHub private vulnerability reporting、`SECURITY.md` 或仓库声明的私密披露渠道。

只有用户明确确认内容适合公开披露且已完全脱敏时，安全相关请求才可以创建公开 issue。Issue body 不得包含原始 secrets、tokens、credentials、private keys、exploit payloads、个人联系方式或私有客户数据。

来源：PR #164，Issue #147。
