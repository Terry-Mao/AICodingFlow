# Staged Review

暂存评审用于处理来源不足、来源冲突或需要产品确认的 wiki 变更。

## 何时暂存

- raw source 没有明确支持该事实。
- 不同 raw source 对同一行为描述冲突。
- 查询发现长期知识缺口，但只能从 issue、PR 描述或实现 diff 推断。
- 页面需要保留问题以便 reviewer 判断，但不能把它写成当前产品事实。

## 写法

- frontmatter 使用 `status: proposed` 或 `status: needs-review`。
- `confidence` 使用 `medium` 或 `low`。
- `source_status` 使用 `partial` 或 `conflict`。
- 正文放在 `## 待确认` 或 `## 开放问题` 下。
- 在 [../log.md](../log.md) 记录待确认项、涉及页面和来源缺口。

## Review Gate

PR reviewer 应确认暂存项是否有足够来源支持：

- 已确认：改为 `status: current`、`source_status: verified`，并把事实移入正常正文。
- 仍不明确：保留暂存状态，补充更具体的开放问题。
- 不成立：删除该事实或改写为历史/反例说明。
