#!/usr/bin/env python3

from __future__ import annotations

import unittest
from unittest.mock import patch

from script_imports import import_script


build_pr_diff = import_script(".github/scripts/build_pr_diff.py", "build_pr_diff")


class BuildPrDiffTest(unittest.TestCase):
    def test_fetch_github_pr_diff_requests_unified_diff_media_type(self) -> None:
        captured = {}

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b"diff --git a/core/foo.py b/core/foo.py\n"

        def fake_urlopen(request: object) -> Response:
            captured["full_url"] = request.full_url
            captured["authorization"] = request.get_header("Authorization")
            captured["accept"] = request.get_header("Accept")
            captured["api_version"] = request.get_header("X-github-api-version")
            return Response()

        with patch.object(build_pr_diff.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token"),
                ["diff --git a/core/foo.py b/core/foo.py"],
            )

        self.assertEqual(captured["full_url"], "https://api.github.com/repos/owner/repo/pulls/42")
        self.assertEqual(captured["authorization"], "Bearer token")
        self.assertEqual(captured["accept"], "application/vnd.github.diff")
        self.assertEqual(captured["api_version"], "2022-11-28")

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
