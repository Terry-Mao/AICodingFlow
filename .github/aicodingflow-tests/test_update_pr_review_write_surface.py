from __future__ import annotations

import unittest

from script_imports import import_script


validator = import_script(
    ".github/skills/update-pr-review/scripts/validate_write_surface.py",
    "validate_update_pr_review_write_surface",
)


class UpdatePrReviewWriteSurfaceTest(unittest.TestCase):
    def test_allows_local_companion_skills(self) -> None:
        self.assertEqual(
            validator.invalid_paths(
                [
                    ".github/skills/review-pr-repo/SKILL.md",
                    ".github/skills/review-spec-repo/SKILL.md",
                ]
            ),
            [],
        )

    def test_blocks_core_review_skill(self) -> None:
        self.assertEqual(
            validator.invalid_paths([".github/skills/review-pr/SKILL.md"]),
            [".github/skills/review-pr/SKILL.md"],
        )

    def test_blocks_product_code(self) -> None:
        self.assertEqual(validator.invalid_paths(["src/app.py"]), ["src/app.py"])


if __name__ == "__main__":
    unittest.main()
