# 自进化 repo SKILL

AICodingFlow 把通用流程和仓库本地偏好分开：

- 核心 SKILL 定义稳定 contract、schema、权限边界和安全规则。
- `*-repo` companion SKILL 只补充目标仓库的本地经验，例如审查偏好、重复 issue 模式、triage 分类习惯。

这样升级 AICodingFlow 时可以继续覆盖核心 SKILL，同时保留目标仓库自己的经验。

## Repo Companion SKILL

常见 companion：

| SKILL | 用途 |
| --- | --- |
| `review-pr-repo` | 普通代码 PR 的仓库本地 review guidance。 |
| `review-spec-repo` | spec-only PR 的仓库本地 review guidance。 |
| `triage-issue-repo` | issue triage 的仓库本地分类、复现和问题模式。 |
| `dedupe-issue-repo` | duplicate issue 的仓库本地识别模式。 |

核心 SKILL 会在允许的范围内读取 companion。companion 不能改变核心 schema、severity、diff-line targeting、protected labels、validator 规则或 GitHub 写操作边界。

## Review Guidance 自进化

Workflow：

```text
.github/workflows/update-pr-review.yml
```

相关 SKILL：

```text
update-pr-review
```

用途：

- 聚合人类对 bot review 的反馈。
- 判断哪些反馈反映了稳定、可复用的仓库规则。
- 更新 `.agents/skills/review-pr-repo/SKILL.md` 和 `.agents/skills/review-spec-repo/SKILL.md`。

适合沉淀的规则：

- 某类代码在本仓库总是需要额外验证。
- 某类 review comment 经常误报，需要缩小触发条件。
- spec 文档在本仓库必须覆盖的固定章节、验收口径或 rollout 要求。

不适合沉淀的内容：

- 单个 PR 的临时上下文。
- 一次性的个人偏好。
- 会绕过核心 validator 或改变 review 输出结构的规则。

## Dedupe Guidance 自进化

Workflow：

```text
.github/workflows/update-dedupe.yml
```

相关 SKILL：

```text
update-dedupe
```

用途：

- 学习最近维护者关闭为 duplicate 的 issue。
- 总结目标仓库常见重复问题簇。
- 更新 `.agents/skills/dedupe-issue-repo/SKILL.md`。

适合沉淀的规则：

- 多个 issue 标题不同但根因相同的模式。
- 某些用户描述、报错文本或复现路径经常对应同一个已知问题。
- 本仓库特有的重复判断口径。

## Triage Guidance

`triage-issue-repo` 目前由人工维护，或通过仓库自己的流程更新。它可以补充：

- label taxonomy 的本地解释。
- 哪些信息缺失时需要追问 reporter。
- 哪些路径、模块或功能域常对应哪些 owner。
- 已知问题簇和复现判断经验。

它不能改变：

- `triage_result.json` 的结构。
- `ready-to-implement`、`ready-to-spec`、`plan-approved` 的 protected label 规则。
- duplicate 和 follow-up questions 互斥的规则。
- issue body、comments、templates 作为不可信数据处理的安全边界。

## 编写 Companion 的原则

- 只写可复用规则，不写一次性结论。
- 用具体证据描述触发条件，避免宽泛偏好。
- 保持规则可验证：说明应该检查哪些文件、artifact、label 或 comment。
- 不要求 agent 调用 GitHub API、发布评论、提交代码或改变 workflow 权限。
- 不复制核心 SKILL 已经规定的 schema 和安全规则。

## 安装和升级时的关系

`install.sh` 会同步核心 `.agents/skills/`。AICodingFlow 仓库自带的 `*-repo` companion 不会安装到目标项目；目标项目已有的 companion skills 会保留不动，并由 `update-*` 系列 SKILL 在有证据时创建或更新。

升级时的建议顺序：

1. 运行 `./install.sh --target /path/to/target-repo --dry-run`。
2. 确认核心 SKILL、scripts 和 workflows 的变更。
3. 正式安装。
4. 保留目标仓库本地的 `*-repo` companion。
5. 让 `update-pr-review` 或 `update-dedupe` 在有足够反馈时再更新 companion。
