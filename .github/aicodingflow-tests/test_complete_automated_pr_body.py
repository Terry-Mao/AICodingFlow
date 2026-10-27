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
        validator.validate_body(result)


if __name__ == "__main__":
    unittest.main()
