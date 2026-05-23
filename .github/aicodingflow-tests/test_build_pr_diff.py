#!/usr/bin/env python3

from __future__ import annotations

import unittest

from script_imports import import_script


build_pr_diff = import_script(".github/scripts/build_pr_diff.py", "build_pr_diff")


class BuildPrDiffTest(unittest.TestCase):
    def test_metadata_only_rename_still_emits_file_section(self) -> None:
        diff = [
            "diff --git a/core/deleted.py b/core/renamed.py",
            "similarity index 100%",
            "rename from core/deleted.py",
            "rename to core/renamed.py",
        ]

        self.assertEqual(
            build_pr_diff.convert(diff),
            "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE core/renamed.py",
                    "END_FILE",
                    "",
                ]
            ),
        )

    def test_hunk_lines_that_look_like_file_headers_are_not_file_headers(self) -> None:
        diff = [
            "diff --git a/docs/example.txt b/docs/example.txt",
            "index 1111111..2222222 100644",
            "--- a/docs/example.txt",
            "+++ b/docs/example.txt",
            "@@ -1,2 +1,3 @@",
            " unchanged",
            "--- old literal",
            "+++ literal content",
            "+next line",
        ]

        self.assertEqual(
            build_pr_diff.convert(diff),
            "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE docs/example.txt",
                    "HUNK @@ -1,2 +1,3 @@",
                    "BOTH     1 | unchanged",
                    "LEFT     2 | -- old literal",
                    "RIGHT    2 | ++ literal content",
                    "RIGHT    3 | next line",
                    "END_FILE",
                    "",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
