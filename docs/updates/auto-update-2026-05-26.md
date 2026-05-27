# Product Change Report: 2026-05-26

Scan window: `2026-05-26T00:00:00Z` inclusive to `2026-05-27T00:00:00Z` exclusive.

## User-visible changes

- Added an automated product change report workflow that scans merged PRs for a UTC report day and generates a time-series update report under `docs/updates/auto-update-YYYY-MM-DD.md`. The workflow can run on schedule or by manual dispatch with an optional report date. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165), commit `fb3749f6f0a4230d51c9d72e2e4532a7d8f12f3d`, refs #87.
- Added a `product-change-report` Codex skill that defines which changes should be included, which files may be modified, and how report entries should remain traceable without changing authoritative product docs. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165).

## Bug fixes

- Hardened the merged-PR search call used by the report context generator to explicitly use `GET` for the GitHub Search API, improving reliability for scheduled report preparation. Source: [PR #166](https://github.com/Terry-Mao/AICodingFlow/pull/166), commit `31ddb1ffd4c36bec75e510ded23f60338a30869b`.

## Behavior changes

- Product change reports now use a deterministic UTC scan window, process merged PRs by `mergedAt` ascending and PR number ascending, and write stable context files before Codex generates the report. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165).
- A ledger at `docs/updates/.product-change-report-ledger.json` records reported PRs so future runs can skip PRs already captured in another report while still allowing same-report reruns. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165).

## Internal engineering changes

- Added scripts for preparing product change report context, updating the report ledger, and writing the automation PR body. The outer workflow owns Git and PR side effects while Codex is limited to generating the report file. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165).
- Added workflow validation that checks Codex only changes the requested report path, verifies prepared context checksums before ledger updates, and uploads the report context artifacts for debugging. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165), commit `7e17623f24bb4c57af98909fdd45371cb9ebb78e`.
- Added tests covering scan window calculation, report path and sort metadata, ledger filtering and reruns, workflow permissions and prompt constraints, context checksum validation, and the GitHub Search API method used by report discovery. Sources: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165), [PR #166](https://github.com/Terry-Mao/AICodingFlow/pull/166).

## Risks or validation needed

- The first scheduled runs should confirm that the configured OpenAI endpoint, GitHub token permissions, report generation prompt, ledger update, and create-or-update PR flow work together in GitHub Actions. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165).
- PR #165 reports local validation with `.github/aicodingflow-tests`, `.github/tests`, and Python compile checks for the new scripts; PR #166 updates the search-method test expectation after the follow-up fix.

## Possible docs sync candidates

- Consider documenting the product change report automation, ledger behavior, manual dispatch date input, and the non-authoritative nature of generated update reports in long-term maintainer or product documentation. Source: [PR #165](https://github.com/Terry-Mao/AICodingFlow/pull/165), refs #87.

## Source references

- [PR #165: docs(skill): add product change report workflow](https://github.com/Terry-Mao/AICodingFlow/pull/165)
- [PR #166: Feat/feature docs 87](https://github.com/Terry-Mao/AICodingFlow/pull/166)
