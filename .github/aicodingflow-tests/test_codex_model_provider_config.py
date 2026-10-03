from __future__ import annotations

import unittest

from script_imports import ROOT


CODEX_WORKFLOWS = (
    ".github/workflows/create-implementation-from-issue.yml",
    ".github/workflows/create-spec-from-issue.yml",
    ".github/workflows/product-change-report.yml",
    ".github/workflows/product-docs-sync.yml",
    ".github/workflows/product-wiki-compile.yml",
    ".github/workflows/respond-to-pr-comment.yml",
    ".github/workflows/review-pr.yml",
    ".github/workflows/triage-issue.yml",
    ".github/workflows/update-dedupe.yml",
    ".github/workflows/update-pr-review.yml",
    ".github/workflows/update-triage.yml",
)
PINNED_REVIEW_ACTION = "uses: openai/codex-action@52fe01ec70a42f454c9d2ebd47598f9fd6893d56"


class CodexModelProviderConfigTest(unittest.TestCase):
    def test_all_codex_workflows_use_shared_provider_configuration(self) -> None:
        for path in CODEX_WORKFLOWS:
            with self.subTest(path=path):
                contents = (ROOT / path).read_text(encoding="utf-8")
                if path.endswith("/review-pr.yml"):
                    self.assertEqual(contents.count(PINNED_REVIEW_ACTION), 1)
                else:
                    self.assertEqual(contents.count("uses: openai/codex-action@v1"), 1)
                self.assertEqual(contents.count("openai-api-key: ${{ secrets.CODEX_API_KEY }}"), 1)
                self.assertEqual(
                    contents.count("model: ${{ vars.CODEX_MODEL }}"),
                    1,
                )
                self.assertEqual(contents.count("CODEX_API_ENDPOINT: ${{ vars.CODEX_API_ENDPOINT }}"), 1)
                self.assertIn('endpoint="${CODEX_API_ENDPOINT%/}"', contents)
                self.assertIn("*/responses", contents)
                self.assertIn("$endpoint/responses", contents)
                self.assertIn("CODEX_API_ENDPOINT is not set", contents)

    def test_workflows_do_not_read_the_legacy_endpoint_environment_directly(self) -> None:
        for path in CODEX_WORKFLOWS:
            with self.subTest(path=path):
                contents = (ROOT / path).read_text(encoding="utf-8")
                self.assertNotIn("OPENAI_", contents)


if __name__ == "__main__":
    unittest.main()
