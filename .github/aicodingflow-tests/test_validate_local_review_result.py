from __future__ import annotations

import unittest

from script_imports import import_script


validator = import_script(".github/scripts/validate_local_review_result.py", "validate_local_review_result")


class ValidateLocalReviewResultTest(unittest.TestCase):
    def test_rejects_legacy_root_review_outputs(self) -> None:
        self.assertEqual(
            validator.validate_records(
                [
                    (" ", "M", "review.json"),
                    (" ", "?", "pr_diff.txt"),
                    (" ", "?", "pr_description.txt"),
                    (" ", "?", "spec_context.md"),
                ]
            ),
            [
                "unexpected file change during local review: review.json",
                "unexpected file change during local review: pr_diff.txt",
                "unexpected file change during local review: pr_description.txt",
                "unexpected file change during local review: spec_context.md",
            ],
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

    def test_parse_status_records_rejects_untracked_review_output(self) -> None:
        records = validator.parse_status_records(b"?? review.json\0")

        self.assertEqual(records, [("?", "?", "review.json")])
        self.assertEqual(
            validator.validate_records(records),
            ["unexpected file change during local review: review.json"],
        )

    def test_rejects_fixed_baseline_file_in_repository_root(self) -> None:
        records = validator.parse_status_records(b"?? .local_review_baseline.status\0")

        self.assertEqual(records, [("?", "?", ".local_review_baseline.status")])
        self.assertEqual(
            validator.validate_records(records),
            ["unexpected file change during local review: .local_review_baseline.status"],
        )

    def test_baseline_allows_existing_worktree_state_only(self) -> None:
        self.assertEqual(
            validator.validate_records_against_baseline(
                [
                    (" ", "M", "src/app.py"),
                    ("A", " ", "src/staged.py"),
                ],
                [
                    (" ", "M", "src/app.py"),
                    ("A", " ", "src/staged.py"),
                ],
            ),
            [],
        )

    def test_baseline_rejects_legacy_root_review_output(self) -> None:
        self.assertEqual(
            validator.validate_records_against_baseline(
                [
                    (" ", "M", "src/app.py"),
                    (" ", "?", "review.json"),
                ],
                [
                    (" ", "M", "src/app.py"),
                ],
            ),
            ["unexpected file change during local review: review.json"],
        )

    def test_baseline_rename_record_does_not_swallow_next_dirty_file(self) -> None:
        baseline = validator.parse_status_records(b"R  core/renamed.py\0core/deleted.py\0 M src/app.py\0")
        current = validator.parse_status_records(b"R  core/renamed.py\0core/deleted.py\0 M src/app.py\0")

        self.assertEqual(
            validator.validate_records_against_baseline(current, baseline),
            [],
        )

    def test_baseline_rejects_new_or_changed_business_state(self) -> None:
        self.assertEqual(
            validator.validate_records_against_baseline(
                [
                    (" ", "M", "src/app.py"),
                    (" ", "M", "src/new.py"),
                ],
                [
                    ("A", " ", "src/app.py"),
                    (" ", "M", "src/removed.py"),
                ],
            ),
            [
                "unexpected file change during local review: src/new.py",
                "baseline file state changed during local review: src/removed.py",
                "baseline file state changed during local review: src/app.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
