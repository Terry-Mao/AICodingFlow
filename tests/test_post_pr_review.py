#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.script_imports import import_script


post_pr_review = import_script(".github/scripts/post_pr_review.py", "post_pr_review")


class PostPrReviewTest(unittest.TestCase):
    def test_parse_diff_positions_maps_review_targets_to_github_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            diff_path = Path(directory) / "pr_diff.txt"
            diff_path.write_text(
                "\n".join(
                    [
                        "# PR_DIFF_V1",
                        "FILE app.py",
                        "HUNK @@ -1,2 +1,3 @@",
                        "BOTH     1 | keep",
                        "LEFT     2 | old",
                        "RIGHT    2 | new",
                        "RIGHT    3 | added",
                        "END_FILE",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                post_pr_review.parse_diff_positions(diff_path),
                {("app.py", "LEFT", 2): 2, ("app.py", "RIGHT", 2): 3, ("app.py", "RIGHT", 3): 4},
            )

    def test_parse_diff_positions_counts_additional_hunk_headers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            diff_path = Path(directory) / "pr_diff.txt"
            diff_path.write_text(
                "\n".join(
                    [
                        "# PR_DIFF_V1",
                        "FILE app.py",
                        "HUNK @@ -1,1 +1,1 @@",
                        "RIGHT    1 | first",
                        "HUNK @@ -20,1 +20,1 @@",
                        "RIGHT   20 | second",
                        "END_FILE",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                post_pr_review.parse_diff_positions(diff_path),
                {("app.py", "RIGHT", 1): 1, ("app.py", "RIGHT", 20): 3},
            )

    def test_normalize_comments_sends_position_payload(self) -> None:
        comments = [
            {
                "path": "app.py",
                "side": "RIGHT",
                "start_line": 2,
                "line": 3,
                "body": "⚠️ [IMPORTANT] issue",
            }
        ]

        self.assertEqual(
            post_pr_review.normalize_comments(comments, {("app.py", "RIGHT", 3): 4}),
            [{"path": "app.py", "position": 4, "body": "⚠️ [IMPORTANT] issue"}],
        )

    def test_normalize_comments_rejects_missing_position(self) -> None:
        comments = [{"path": "app.py", "side": "RIGHT", "line": 3, "body": "body"}]

        with self.assertRaisesRegex(SystemExit, "comment target is missing from diff positions"):
            post_pr_review.normalize_comments(comments, {})

    def test_main_posts_review_with_diff_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps(
                    {
                        "body": "summary",
                        "comments": [
                            {
                                "path": "app.py",
                                "side": "RIGHT",
                                "line": 2,
                                "body": "⚠️ [IMPORTANT] issue",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
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

            with (
                mock.patch.dict(
                    os.environ,
                    {"GITHUB_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo"},
                    clear=True,
                ),
                mock.patch.object(
                    post_pr_review,
                    "load_event",
                    return_value={"pull_request": {"number": 5, "head": {"sha": "abc123"}}},
                ),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}) as request_json,
                mock.patch(
                    "sys.argv",
                    ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)],
                ),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_json.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/5/reviews",
            "token",
            {
                "event": "COMMENT",
                "commit_id": "abc123",
                "body": "summary",
                "comments": [{"path": "app.py", "position": 1, "body": "⚠️ [IMPORTANT] issue"}],
            },
        )

    def test_main_posts_body_only_review_without_diff_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            review_path.write_text('{"body": "summary", "comments": []}', encoding="utf-8")

            with (
                mock.patch.dict(
                    os.environ,
                    {"GITHUB_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo"},
                    clear=True,
                ),
                mock.patch.object(
                    post_pr_review,
                    "load_event",
                    return_value={"pull_request": {"number": 5, "head": {"sha": "abc123"}}},
                ),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}) as request_json,
                mock.patch("sys.argv", ["post_pr_review.py", "--review", str(review_path)]),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_json.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/5/reviews",
            "token",
            {
                "event": "COMMENT",
                "commit_id": "abc123",
                "body": "summary",
                "comments": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
