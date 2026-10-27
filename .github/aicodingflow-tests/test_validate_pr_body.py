from __future__ import annotations

import unittest

from script_imports import import_script


validator = import_script(".github/scripts/validate_pr_body.py", "validate_pr_body")


class ValidatePrBodyTests(unittest.TestCase):
    def test_accepts_completed_sections(self) -> None:
        validator.validate_body("## Summary\nChange.\n## Testing\nUnit tests passed.\n## Risk\nLow.\n## How to revert\nRevert commit.")

    def test_template_comments_are_not_content(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Testing, Risk, How to revert"):
            validator.validate_body("## Summary\nChange.\n## Testing\n<!-- fill -->\n## Risk\n\n## How to revert\n")

    def test_code_fence_does_not_supply_sections(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Testing"):
            validator.validate_body("## Summary\nChange.\n```md\n## Testing\nDone\n## Risk\nLow\n## How to revert\nRevert\n```\n")

    def test_tilde_fence_does_not_supply_sections(self) -> None:
        example = "~~~markdown\n## Summary\nChange\n## Testing\nPassed\n## Risk\nLow\n## How to revert\nRevert\n~~~"
        with self.assertRaisesRegex(SystemExit, "Summary, Testing, Risk, How to revert"):
            validator.validate_body(example)

    def test_longer_fence_ignores_shorter_inner_fence(self) -> None:
        body = "## Summary\nChange.\n~~~~markdown\n~~~\n## Testing\nPassed\n~~~~\n## Risk\nLow.\n## How to revert\nRevert."
        with self.assertRaisesRegex(SystemExit, "Testing"):
            validator.validate_body(body)

    def test_real_sections_after_tilde_fence_are_accepted(self) -> None:
        body = "~~~markdown\n## Testing\nExample\n~~~\n## Summary\nChange.\n## Testing\nPassed.\n## Risk\nLow.\n## How to revert\nRevert."
        validator.validate_body(body)


if __name__ == "__main__":
    unittest.main()
