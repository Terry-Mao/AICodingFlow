from __future__ import annotations

import unittest

from script_imports import import_script


complete = import_script(".github/scripts/complete_automated_pr_body.py", "complete_automated_pr_body")
validator = import_script(".github/scripts/validate_pr_body.py", "validate_pr_body_for_automation")


class CompleteAutomatedPrBodyTests(unittest.TestCase):
    def test_adds_missing_sections_and_preserves_summary(self) -> None:
        result = complete.complete_body("Generated report for yesterday.", "Product Change Report", "低")
        validator.validate_body(result)
        self.assertIn("## Summary\n\nGenerated report for yesterday.", result)
        self.assertIn("Product Change Report", result)
        self.assertIn("## Risk\n\n低：", result)

    def test_keeps_existing_sections(self) -> None:
        body = "## Summary\n\nExisting.\n\n## Testing\n\nActual test passed."
        result = complete.complete_body(body, "Example", "中")
        self.assertEqual(result.count("## Testing"), 1)
        self.assertIn("Actual test passed.", result)
        validator.validate_body(result)

    def test_fills_existing_empty_sections_without_duplicating_headings(self) -> None:
        body = (
            "## Summary\n\nGenerated report.\n\n"
            "## Testing\n\n"
            "## Risk\n<!-- fill later -->\n\n"
            "## How to revert\n   \n"
        )
        result = complete.complete_body(body, "Product Docs Sync", "低")
        validator.validate_body(result)
        sections = validator.section_contents(result)
        self.assertEqual(sections["testing"], "由 Product Docs Sync 生成；校验结果见对应的 GitHub Actions run。")
        self.assertEqual(sections["risk"], "低：自动生成内容可能不准确，需要在 PR 中核对。")
        self.assertEqual(sections["how to revert"], "回滚此 PR 的合并提交。")
        for name in complete.HEADINGS:
            self.assertEqual(result.count(f"## {name}\n"), 1)

    def test_fills_existing_empty_summary(self) -> None:
        body = "## Summary\n\n## Testing\nTests passed."
        result = complete.complete_body(body, "Product Docs Sync", "低")
        validator.validate_body(result)
        self.assertEqual(result.count("## Summary"), 1)
        self.assertIn("由 Product Docs Sync 生成；具体变更见本 PR 的文件改动。", validator.section_contents(result)["summary"])

    def test_ignores_headings_in_fenced_examples(self) -> None:
        body = "Generated report.\n\n~~~markdown\n## Testing\nExample only.\n## Risk\nExample only.\n## How to revert\nExample only.\n~~~"
        result = complete.complete_body(body, "Product Docs Sync", "低")
        validator.validate_body(result)
        self.assertIn("~~~markdown\n## Testing\nExample only.", result)
        self.assertIn("## Testing\n\n由 Product Docs Sync 生成", result)
        self.assertIn("## Risk\n\n低：", result)

    def test_keeps_testing_section_with_only_fenced_code(self) -> None:
        body = "## Summary\n\nGenerated report.\n\n## Testing\n\n```sh\npython3 -m unittest\n```"
        result = complete.complete_body(body, "Product Docs Sync", "低")
        self.assertEqual(result.count("## Testing"), 1)
        self.assertNotIn("校验结果见对应的 GitHub Actions run", result)
        validator.validate_body(result)


if __name__ == "__main__":
    unittest.main()
