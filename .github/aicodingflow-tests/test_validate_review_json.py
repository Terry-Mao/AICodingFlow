#!/usr/bin/env python3

from __future__ import annotations

import unittest
import json
import tempfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock

from script_imports import import_script


validate_review_json = import_script(".github/scripts/validate_review_json.py", "validate_review_json")


class ValidateReviewJsonTest(unittest.TestCase):
    def test_require_type_rejects_bool_for_int(self) -> None:
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as context:
            validate_review_json.require_type(True, int, "comments[0].line")
        self.assertEqual(context.exception.code, 1)

    def run_validator(self, review: dict[str, object]) -> int | None:
        with tempfile.TemporaryDirectory() as directory:
            diff_path = Path(directory) / "pr_diff.txt"
            review_path = Path(directory) / "review.json"
            diff_path.write_text(
                "\n".join(
                    [
                        "# PR_DIFF_V1",
                        "FILE app.py",
                        "HUNK @@ -1,1 +1,1 @@",
                        "RIGHT    2 | new",
                        "END_FILE",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            review_path.write_text(json.dumps(review), encoding="utf-8")
            with mock.patch("sys.argv", ["validate_review_json.py", str(diff_path), str(review_path)]):
                result = validate_review_json.main()
        return result

    def assert_validator_fails(self, review: dict[str, object], message: str) -> None:
        with redirect_stderr(StringIO()) as stderr, self.assertRaises(SystemExit) as context:
            self.run_validator(review)
        self.assertEqual(context.exception.code, 1)
        self.assertIn(message, stderr.getvalue())

    def test_accepts_minimal_approve_review(self) -> None:
        self.assertIsNone(self.run_validator({"verdict": "APPROVE", "body": "summary", "comments": []}))

    def test_accepts_reject_review_and_single_reviewer(self) -> None:
        self.assertIsNone(
            self.run_validator(
                {
                    "verdict": "REJECT",
                    "body": "",
                    "comments": [],
                    "recommended_reviewers": ["reviewer-login"],
                }
            )
        )

    def test_rejects_missing_verdict(self) -> None:
        self.assert_validator_fails({"body": "", "comments": []}, "review.verdict is required")

    def test_rejects_unknown_verdict(self) -> None:
        self.assert_validator_fails(
            {"verdict": "COMMENT", "body": "", "comments": []},
            "review.verdict must be APPROVE or REJECT",
        )

    def test_rejects_multiple_recommended_reviewers(self) -> None:
        self.assert_validator_fails(
            {
                "verdict": "APPROVE",
                "body": "",
                "comments": [],
                "recommended_reviewers": ["one", "two"],
            },
            "review.recommended_reviewers must contain at most 1 reviewer",
        )

    def test_rejects_non_string_recommended_reviewer(self) -> None:
        self.assert_validator_fails(
            {
                "verdict": "APPROVE",
                "body": "",
                "comments": [],
                "recommended_reviewers": [123],
            },
            "review.recommended_reviewers[0] must be str",
        )


if __name__ == "__main__":
    unittest.main()
