#!/usr/bin/env python3

from __future__ import annotations

import unittest
from contextlib import redirect_stderr
from io import StringIO

from tests.script_imports import import_script


validate_review_json = import_script("skills/review-pr/scripts/validate_review_json.py", "validate_review_json")


class ValidateReviewJsonTest(unittest.TestCase):
    def test_require_type_rejects_bool_for_int(self) -> None:
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as context:
            validate_review_json.require_type(True, int, "comments[0].line")
        self.assertEqual(context.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
