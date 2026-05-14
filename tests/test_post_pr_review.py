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

    def test_changed_files_from_diff_preserves_first_seen_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            diff_path = Path(directory) / "pr_diff.txt"
            diff_path.write_text(
                "\n".join(["FILE app.py", "END_FILE", "FILE specs/x.md", "END_FILE", "FILE app.py", "END_FILE"]),
                encoding="utf-8",
            )

            self.assertEqual(post_pr_review.changed_files_from_diff(diff_path), ["app.py", "specs/x.md"])

    def test_normalize_comments_preserves_range_payload(self) -> None:
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
            [
                {
                    "path": "app.py",
                    "line": 3,
                    "side": "RIGHT",
                    "start_line": 2,
                    "start_side": "RIGHT",
                    "body": "⚠️ [IMPORTANT] issue",
                }
            ],
        )

    def test_normalize_comments_rejects_missing_position(self) -> None:
        comments = [{"path": "app.py", "side": "RIGHT", "line": 3, "body": "body"}]

        with self.assertRaisesRegex(SystemExit, "comment target is missing from diff positions"):
            post_pr_review.normalize_comments(comments, {})

    def test_review_event_matrix_and_conservative_author_handling(self) -> None:
        member = {"author_association": "MEMBER", "user": {"login": "maintainer", "type": "User"}}
        non_member = {"author_association": "CONTRIBUTOR", "user": {"login": "contrib", "type": "User"}}
        bot = {"author_association": "CONTRIBUTOR", "user": {"login": "renovate[bot]", "type": "Bot"}}
        unknown = {"user": {"login": "maybe", "type": "User"}}

        self.assertEqual(post_pr_review.review_event_for(member, ["app.py"], "APPROVE"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(member, ["app.py"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member, ["app.py"], "APPROVE"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member, ["app.py"], "REJECT"), "REQUEST_CHANGES")
        self.assertEqual(post_pr_review.review_event_for(non_member, ["specs/x.md"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(bot, ["app.py"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(unknown, ["app.py"], "REJECT"), "COMMENT")

    def test_select_reviewer_prefers_valid_recommendation(self) -> None:
        rules = [post_pr_review.CodeownersRule("*", ("@maintainer",))]

        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["maintainer"]}, rules, ["app.py"], "contrib"
            ),
            "maintainer",
        )

    def test_select_reviewer_falls_back_from_invalid_recommendations(self) -> None:
        rules = [
            post_pr_review.CodeownersRule("*", ("@first",)),
            post_pr_review.CodeownersRule("src/*", ("@second", "@contrib")),
        ]

        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["contrib"]}, rules, ["src/app.py"], "contrib"
            ),
            "second",
        )
        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["outsider"]}, rules, ["docs/readme.md"], "contrib"
            ),
            "first",
        )
        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["first", "second"]}, rules, ["none/path.py"], "contrib"
            ),
            "first",
        )

    def test_select_reviewer_returns_none_without_eligible_owner(self) -> None:
        rules = [post_pr_review.CodeownersRule("*", ("@org/team", "@contrib"))]

        self.assertIsNone(post_pr_review.select_reviewer({}, rules, ["app.py"], "contrib"))

    def test_main_posts_review_with_diff_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps(
                    {
                        "verdict": "APPROVE",
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
            review_path.write_text('{"verdict": "REJECT", "body": "summary", "comments": []}', encoding="utf-8")

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

    def test_main_requests_reviewer_for_non_member_approved_code_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "APPROVE", "body": "summary", "comments": [], "recommended_reviewers": ["maintainer"]}),
                encoding="utf-8",
            )
            diff_path.write_text("FILE app.py\nEND_FILE\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo"}, clear=True),
                mock.patch.object(
                    post_pr_review,
                    "load_event",
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "CONTRIBUTOR",
                            "user": {"login": "contrib", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(
                    post_pr_review,
                    "parse_codeowners",
                    return_value=[post_pr_review.CodeownersRule("*", ("@maintainer",))],
                ),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}) as request_json,
                mock.patch("sys.argv", ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)]),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(request_json.call_args_list[1].args[0], "https://api.github.com/repos/owner/repo/pulls/5/requested_reviewers")
        self.assertEqual(request_json.call_args_list[1].args[2], {"reviewers": ["maintainer"]})

    def test_main_does_not_request_reviewer_for_spec_only_reject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(json.dumps({"verdict": "REJECT", "body": "summary", "comments": []}), encoding="utf-8")
            diff_path.write_text("FILE specs/product.md\nEND_FILE\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo"}, clear=True),
                mock.patch.object(
                    post_pr_review,
                    "load_event",
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "CONTRIBUTOR",
                            "user": {"login": "contrib", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}) as request_json,
                mock.patch("sys.argv", ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)]),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_json.assert_called_once()
        self.assertEqual(request_json.call_args.args[2]["event"], "COMMENT")


if __name__ == "__main__":
    unittest.main()
