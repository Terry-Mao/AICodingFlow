# Page Types

## Summary

summary 页面位于 `docs/product/wiki/summaries/`，每个页面对应一个有意义的 raw 产品文档。

必需 frontmatter:

```yaml
---
type: summary
title: 非空标题
sources:
  - docs/product/raw/example.md
---
```

summary 应包含：

- durable product knowledge，而不是临时实现细节。
- 对相关 concept 页的链接。
- 对 raw source 的相对链接，便于核验精确事实。

## Concept

concept 页面位于 `docs/product/wiki/concepts/`，用于聚合跨源或高价值查询主题，例如 workflow、角色、状态、规则、自动化边界和 recurring decisions。

必需 frontmatter:

```yaml
---
type: concept
title: 非空标题
sources:
  - docs/product/raw/example.md
---
```

concept 应包含：

- 当前可确认的产品行为。
- supporting summaries 链接。
- related concepts 链接。
- 对 `待确认` 或 `开放问题` 的明确标记。
