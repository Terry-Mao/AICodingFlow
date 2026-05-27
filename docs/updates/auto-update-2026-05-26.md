# Product Change Report: 2026-05-26

Scan window: `2026-05-26T00:00:00Z` inclusive to `2026-05-27T00:00:00Z` exclusive.

## User-visible changes

- Added the product change report workflow for daily update reports under `docs/updates/`. The workflow scans merged PRs for a UTC calendar day, prepares stable context and diffs, asks Codex to generate only the dated report file, and leaves Git, ledger, and PR side effects to the outer GitHub Actions job. Source: PR #165, commit `fb3749f6f0a4230d51c9d72e2e4532a7d8f12f3d`, Refs #87.

## Bug fixes

- Fixed the product report merged-PR search to call the GitHub Search API with an explicit `GET` method, keeping scheduled and manual report context generation aligned with the endpoint's expected request shape. Source: PR #166, commit `31ddb1ffd4c36bec75e510ded23f60338a30869b`.

## Behavior changes

- The reporting workflow now validates the generated context checksum after Codex runs and before updating the ledger. This helps ensure the source context files used for report generation were not changed during report writing. Source: PR #165, commit `7e17623f24bb4c57af98909fdd45371cb9ebb78e`.
- The report context script now reuses the detailed PR records returned by its merged-PR fetch path instead of fetching each PR's details a second time, reducing duplicated GitHub CLI calls during context preparation. Source: PR #165, commit `7e17623f24bb4c57af98909fdd45371cb9ebb78e`.

## Internal engineering changes

- Added the `product-change-report` Codex skill, context preparation script, ledger update script, PR body writer, scheduled/manual GitHub Actions workflow, and regression tests for scan windows, ledger filtering, pagination, workflow write-surface validation, and PR body output. Source: PR #165.

## Risks or validation needed

- The first scheduled runs should be checked for end-to-end behavior: context generation, Codex write-surface validation, ledger update, branch creation, and PR creation or update all depend on GitHub Actions permissions, `OPENAI_API_ENDPOINT`, `OPENAI_API_KEY`, and GitHub CLI behavior. Source: PR #165.

## Possible docs sync candidates

- Consider documenting the new product change report workflow in long-term contributor or operations docs if maintainers want this automation to be discoverable outside time-series update reports. Source: PR #165, Refs #87.

## Source references

- PR #165: https://github.com/Terry-Mao/AICodingFlow/pull/165
- PR #166: https://github.com/Terry-Mao/AICodingFlow/pull/166
- Related issue reference: #87
