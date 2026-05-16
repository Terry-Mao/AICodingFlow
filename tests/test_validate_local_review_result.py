from __future__ import annotations

import unittest

from tests.script_imports import import_script


validator = import_script(".github/scripts/validate_local_review_result.py", "validate_local_review_result")


class ValidateLocalReviewResultTest(unittest.TestCase):
    def test_allows_unstaged_local_review_outputs(self) -> None:
        self.assertEqual(
            validator.validate_records(
                [
                    (" ", "M", "review.json"),
                    (" ", "?", "pr_diff.txt"),
                    (" ", "?", "pr_description.txt"),
                    (" ", "?", "spec_context.md"),
                ]
            ),
            [],
        )

    def test_rejects_staged_changes_even_for_review_outputs(self) -> None:
        self.assertEqual(
            validator.validate_records([("A", " ", "review.json")]),
            ["staged change is not allowed during local review: review.json"],
        )

    def test_rejects_source_file_changes(self) -> None:
        self.assertEqual(
            validator.validate_records([(" ", "M", ".github/scripts/build_pr_diff.py")]),
            ["unexpected file change during local review: .github/scripts/build_pr_diff.py"],
        )

    def test_parse_status_records_keeps_rename_destination(self) -> None:
        records = validator.parse_status_records(b" R new.py\0old.py\0")

        self.assertEqual(records, [(" ", "R", "new.py")])

    def test_parse_status_records_accepts_untracked_review_output(self) -> None:
        records = validator.parse_status_records(b"?? review.json\0")

        self.assertEqual(records, [("?", "?", "review.json")])
        self.assertEqual(validator.validate_records(records), [])


if __name__ == "__main__":
    unittest.main()
