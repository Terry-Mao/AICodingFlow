#!/usr/bin/env python3

from __future__ import annotations

import unittest
from unittest.mock import patch

from script_imports import import_script


build_pr_diff = import_script(".github/scripts/build_pr_diff.py", "build_pr_diff")


class BuildPrDiffTest(unittest.TestCase):
    def test_fetch_github_pr_diff_validates_snapshot_and_requests_unified_diff_media_type(self) -> None:
        captured = []

        class Response:
            def __init__(self, body: bytes) -> None:
                self.body = body

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body

        def fake_urlopen(request: object) -> Response:
            captured.append(
                {
                    "full_url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "accept": request.get_header("Accept"),
                    "api_version": request.get_header("X-github-api-version"),
                }
            )
            if len(captured) == 1:
                return Response(b'{"head":{"sha":"head-sha"},"base":{"sha":"base-sha"}}')
            if len(captured) == 2:
                return Response(b"diff --git a/core/foo.py b/core/foo.py\n")
            return Response(b'{"head":{"sha":"head-sha"},"base":{"sha":"base-sha"}}')

        with patch.object(build_pr_diff.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "base-sha"),
                ["diff --git a/core/foo.py b/core/foo.py"],
            )

        self.assertEqual([call["full_url"] for call in captured], ["https://api.github.com/repos/owner/repo/pulls/42"] * 3)
        self.assertEqual([call["authorization"] for call in captured], ["Bearer token"] * 3)
        self.assertEqual(captured[0]["accept"], "application/vnd.github+json")
        self.assertEqual(captured[1]["accept"], "application/vnd.github.diff")
        self.assertEqual(captured[2]["accept"], "application/vnd.github+json")
        self.assertEqual([call["api_version"] for call in captured], ["2022-11-28"] * 3)

    def test_fetch_github_pr_diff_fails_when_head_changes_after_diff_fetch(self) -> None:
        metadata = [
            {"head": {"sha": "head-sha"}, "base": {"sha": "base-sha"}},
            {"head": {"sha": "new-head"}, "base": {"sha": "base-sha"}},
        ]

        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return metadata.pop(0)

        with patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata):
            with patch.object(build_pr_diff, "github_request", return_value=b"diff --git a/core/foo.py b/core/foo.py\n"):
                with self.assertRaisesRegex(SystemExit, "head changed"):
                    build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "base-sha")

    def test_fetch_github_pr_diff_fails_when_head_changed(self) -> None:
        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return {"head": {"sha": "new-head"}, "base": {"sha": "base-sha"}}

        with patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata):
            with self.assertRaisesRegex(SystemExit, "head changed"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "old-head", "base-sha")

    def test_fetch_github_pr_diff_fails_when_base_changed(self) -> None:
        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return {"head": {"sha": "head-sha"}, "base": {"sha": "new-base"}}

        with patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata):
            with self.assertRaisesRegex(SystemExit, "base changed"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "old-base")

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
