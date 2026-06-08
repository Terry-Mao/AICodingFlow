---
type: concept
title: 安全补充 review
status: current
confidence: high
source_status: verified
owner: product-docs
last_reviewed: 2026-05-31
review_due: 2026-08-29
sources:
  - docs/product/raw/pr-review-verdict.md
---

# 安全补充 review

AI PR Review 会把安全补充检查合并进基础 review，而不是生成独立评审输出。

## 应用范围

- Code PR review 会在基础 `review-pr` 之外应用 `security-review-pr`。
- Spec-only PR review 会在基础 `review-spec` 之外应用 `security-review-spec`。
- `security-review-pr` 关注代码层面的安全问题，包括输入校验、注入风险、鉴权与权限检查、secrets 管理、弱加密或错误随机数、依赖与 supply chain、敏感数据处理，以及不安全默认配置。
- `security-review-spec` 关注设计层安全缺口，包括 threat surface、trust boundary、鉴权与授权模型、敏感数据与 secrets 处理、滥用或 DoS 风险、依赖边界、配置默认值，以及安全相关可观测性。

## 输出边界

- 安全发现合并进同一个 `review.json`，不会生成单独输出。
- 安全补充必须遵守 `.agents/contracts/review.md`，不能改变 `review.json` schema、diff-line targeting 或 GitHub/API 边界。
- 安全补充只报告有证据的问题。
- 安全补充不运行动态扫描，不查询外部安全 API，不制造理论风险，也不直接发布 GitHub comment。
- 安全发现的 review comment 使用 `[SECURITY]` 标签。
- 安全发现计入同一个 `review.json.verdict` 判断；critical security finding 通常应导致 `REJECT`。

## Supporting Summaries

- [PR review verdict 与 non-member gate 摘要](../summaries/pr-review-verdict.md)

## Related Concepts

- [AI PR Review workflow](ai-pr-review-workflow.md)
- [PR review verdict](pr-review-verdict.md)
