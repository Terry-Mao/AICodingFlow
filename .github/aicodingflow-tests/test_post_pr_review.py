#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


post_pr_review = import_script(".github/scripts/post_pr_review.py", "post_pr_review")


class PostPrReviewTest(unittest.TestCase):
    def test_review_event_matrix_keeps_member_and_spec_reviews_as_comments(self) -> None:
        member_pr = {"author_association": "MEMBER", "user": {"login": "member", "type": "User"}}
        non_member_pr = {"author_association": "FIRST_TIMER", "user": {"login": "external", "type": "User"}}

        self.assertEqual(post_pr_review.review_event_for(member_pr, ["app.py"], "APPROVE"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(member_pr, ["app.py"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member_pr, ["specs/issue-1/product.md"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member_pr, ["app.py"], "APPROVE"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member_pr, ["app.py"], "REJECT"), "REQUEST_CHANGES")

    def test_spec_only_pr_is_not_a_non_member_code_review_subject(self) -> None:
        non_member_pr = {"author_association": "FIRST_TIMER", "user": {"login": "external", "type": "User"}}

        self.assertFalse(
            post_pr_review.is_non_member_code_review_subject(
                non_member_pr,
                ["specs/issue-1/product.md"],
            )
        )
        self.assertFalse(post_pr_review.should_request_human_reviewer(non_member_pr, ["specs/issue-1/product.md"], "APPROVE"))
        self.assertEqual(post_pr_review.review_event_for(non_member_pr, ["specs/issue-1/product.md"], "APPROVE"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(non_member_pr, ["specs/issue-1/product.md"], "REJECT"), "COMMENT")

    def test_review_event_uses_conservative_author_handling(self) -> None:
        bot_pr = {"author_association": "NONE", "user": {"login": "dependabot[bot]", "type": "Bot"}}
        missing_association_pr = {"user": {"login": "external", "type": "User"}}
        unknown_association_pr = {"author_association": "UNKNOWN", "user": {"login": "external", "type": "User"}}

        self.assertEqual(post_pr_review.review_event_for(bot_pr, ["app.py"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(missing_association_pr, ["app.py"], "REJECT"), "COMMENT")
        self.assertEqual(post_pr_review.review_event_for(unknown_association_pr, ["app.py"], "REJECT"), "COMMENT")

    def test_select_reviewer_prefers_valid_recommendation(self) -> None:
        rules = [
            post_pr_review.CodeownersRule("*.py", ["@fallback"]),
            post_pr_review.CodeownersRule("app.py", ["@preferred"]),
        ]

        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["preferred"]},
                rules,
                ["app.py"],
                "external",
            ),
            "preferred",
        )

    def test_select_reviewer_falls_back_when_recommendation_is_invalid(self) -> None:
        rules = [
            post_pr_review.CodeownersRule("*.py", ["@fallback"]),
            post_pr_review.CodeownersRule("app.py", ["@owner"]),
        ]

        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["external"]},
                rules,
                ["app.py"],
                "external",
            ),
            "owner",
        )
        self.assertEqual(
            post_pr_review.select_reviewer(
                {"recommended_reviewers": ["not-a-codeowner"]},
                rules,
                ["app.py"],
                "external",
            ),
            "owner",
        )

    def test_select_reviewer_uses_first_codeowner_when_no_file_rule_matches(self) -> None:
        rules = [post_pr_review.CodeownersRule("docs/*", ["@docs-owner"])]

        self.assertEqual(post_pr_review.select_reviewer({}, rules, ["app.py"], "external"), "docs-owner")

    def test_codeowners_single_star_does_not_cross_path_separator(self) -> None:
        self.assertTrue(post_pr_review.codeowners_pattern_matches("docs/*", "docs/file.md"))
        self.assertFalse(post_pr_review.codeowners_pattern_matches("docs/*", "docs/private/file.md"))
        self.assertTrue(post_pr_review.codeowners_pattern_matches("docs/**", "docs/private/file.md"))
        self.assertTrue(post_pr_review.codeowners_pattern_matches("*.py", "src/app.py"))

    def test_select_reviewer_uses_last_matching_codeowners_rule_with_path_semantics(self) -> None:
        rules = [
            post_pr_review.CodeownersRule("docs/private/**", ["@private-owner"]),
            post_pr_review.CodeownersRule("docs/*", ["@docs-owner"]),
        ]

        self.assertEqual(
            post_pr_review.select_reviewer({}, rules, ["docs/private/file.md"], "external"),
            "private-owner",
        )

    def test_select_reviewer_returns_none_without_eligible_owner(self) -> None:
        rules = [
            post_pr_review.CodeownersRule("app.py", ["@external"]),
            post_pr_review.CodeownersRule("*", ["@org/team"]),
        ]

        self.assertIsNone(post_pr_review.select_reviewer({}, rules, ["app.py"], "external"))

    def test_dismiss_stale_bot_request_changes_dismisses_only_current_bot_reviews(self) -> None:
        calls = []

        def fake_api(url: str, token: str, *, method: str = "GET", payload: dict | None = None):
            calls.append((url, token, method, payload))
            return {}

        with (
            mock.patch.object(
                post_pr_review,
                "list_pull_request_reviews",
                return_value=[
                    {"id": 10, "state": "CHANGES_REQUESTED", "user": {"login": "github-actions[bot]", "type": "Bot"}},
                    {"id": 11, "state": "CHANGES_REQUESTED", "user": {"login": "maintainer", "type": "User"}},
                    {"id": 12, "state": "COMMENTED", "user": {"login": "github-actions[bot]", "type": "Bot"}},
                    {"id": 13, "state": "CHANGES_REQUESTED", "user": {"login": "other-bot", "type": "Bot"}},
                ],
            ),
            mock.patch.object(post_pr_review, "github_api_json", side_effect=fake_api),
        ):
            post_pr_review.dismiss_stale_bot_request_changes(
                "owner/repo",
                "token",
                {"number": 5},
                post_pr_review.DEFAULT_REVIEW_BOT_LOGIN,
            )

        self.assertEqual(
            calls,
            [
                (
                    "https://api.github.com/repos/owner/repo/pulls/5/reviews/10/dismissals",
                    "token",
                    "PUT",
                    {"message": "Superseded by a later bot approval.", "event": "DISMISS"},
                ),
            ],
        )

    def test_list_pull_request_reviews_follows_pagination(self) -> None:
        calls = []

        def fake_response(url: str, token: str, *, method: str = "GET", payload: dict | None = None):
            calls.append((url, token, method, payload))
            if "page=2" in url:
                return post_pr_review.GitHubResponse(
                    [{"id": 2, "state": "CHANGES_REQUESTED", "user": {"login": "github-actions[bot]", "type": "Bot"}}],
                    {},
                )
            return post_pr_review.GitHubResponse(
                [{"id": 1, "state": "COMMENTED", "user": {"login": "github-actions[bot]", "type": "Bot"}}],
                {"Link": '<https://api.github.com/repos/owner/repo/pulls/5/reviews?per_page=100&page=2>; rel="next"'},
            )

        with mock.patch.object(post_pr_review, "github_api_response", side_effect=fake_response):
            self.assertEqual(
                post_pr_review.list_pull_request_reviews("owner/repo", "token", 5),
                [
                    {"id": 1, "state": "COMMENTED", "user": {"login": "github-actions[bot]", "type": "Bot"}},
                    {"id": 2, "state": "CHANGES_REQUESTED", "user": {"login": "github-actions[bot]", "type": "Bot"}},
                ],
            )

        self.assertEqual(
            calls,
            [
                ("https://api.github.com/repos/owner/repo/pulls/5/reviews?per_page=100", "token", "GET", None),
                ("https://api.github.com/repos/owner/repo/pulls/5/reviews?per_page=100&page=2", "token", "GET", None),
            ],
        )

    def test_dismiss_stale_bot_request_changes_skips_when_listing_reviews_fails(self) -> None:
        with (
            mock.patch.object(
                post_pr_review,
                "list_pull_request_reviews",
                side_effect=SystemExit("transient failure"),
            ) as list_reviews,
            mock.patch("builtins.print") as print_mock,
        ):
            post_pr_review.dismiss_stale_bot_request_changes(
                "owner/repo",
                "token",
                {"number": 5},
                post_pr_review.DEFAULT_REVIEW_BOT_LOGIN,
            )

        list_reviews.assert_called_once_with("owner/repo", "token", 5)
        print_mock.assert_called_once_with(
            "Could not read PR reviews; skipping stale request-changes dismissal: transient failure"
        )

    def test_review_author_matches_configured_bot_login_and_bot_identity(self) -> None:
        self.assertTrue(
            post_pr_review.review_author_matches_bot(
                {"user": {"login": "custom-review-bot", "type": "Bot"}},
                "custom-review-bot",
            )
        )
        self.assertFalse(
            post_pr_review.review_author_matches_bot(
                {"user": {"login": "other-bot", "type": "Bot"}},
                "custom-review-bot",
            )
        )
        self.assertFalse(
            post_pr_review.review_author_matches_bot(
                {"user": {"login": "custom-review-bot", "type": "User"}},
                "custom-review-bot",
            )
        )
        self.assertTrue(
            post_pr_review.review_author_matches_bot(
                {"user": {"login": "custom-review-bot[bot]"}},
                "custom-review-bot[bot]",
            )
        )

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

    def test_main_posts_review_with_diff_positions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps(
                    {
                        "verdict": "REJECT",
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "MEMBER",
                            "user": {"login": "member", "type": "User"},
                        }
                    },
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
            review_path.write_text('{"verdict": "APPROVE", "body": "summary", "comments": []}', encoding="utf-8")

            with (
                mock.patch.dict(
                    os.environ,
                    {"GITHUB_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo"},
                    clear=True,
                ),
                mock.patch.object(
                    post_pr_review,
                    "load_event",
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "MEMBER",
                            "user": {"login": "member", "type": "User"},
                        }
                    },
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

    def test_main_posts_request_changes_for_non_member_rejected_code_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "REJECT", "body": "blocking issue", "comments": []}),
                encoding="utf-8",
            )
            diff_path.write_text(
                "\n".join(["# PR_DIFF_V1", "FILE app.py", "END_FILE", ""]),
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "FIRST_TIMER",
                            "user": {"login": "external", "type": "User"},
                        }
                    },
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
                "event": "REQUEST_CHANGES",
                "commit_id": "abc123",
                "body": "blocking issue",
                "comments": [],
            },
        )

    def test_main_requests_reviewer_for_non_member_approved_code_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "APPROVE", "body": "summary", "comments": []}),
                encoding="utf-8",
            )
            diff_path.write_text(
                "\n".join(["# PR_DIFF_V1", "FILE app.py", "END_FILE", ""]),
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "NONE",
                            "user": {"login": "external", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(post_pr_review, "parse_codeowners", return_value=[post_pr_review.CodeownersRule("*", ["@owner"])]),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}),
                mock.patch.object(post_pr_review, "list_pull_request_reviews", return_value=[]),
                mock.patch.object(post_pr_review, "request_reviewer") as request_reviewer,
                mock.patch(
                    "sys.argv",
                    ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)],
                ),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_reviewer.assert_called_once_with("owner/repo", "token", 5, "owner")

    def test_main_requests_reviewer_for_empty_non_member_approved_code_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "APPROVE", "body": "", "comments": []}),
                encoding="utf-8",
            )
            diff_path.write_text(
                "\n".join(["# PR_DIFF_V1", "FILE app.py", "END_FILE", ""]),
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "NONE",
                            "user": {"login": "external", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(post_pr_review, "parse_codeowners", return_value=[post_pr_review.CodeownersRule("*", ["@owner"])]),
                mock.patch.object(post_pr_review, "list_pull_request_reviews", return_value=[]),
                mock.patch.object(post_pr_review, "request_json") as request_json,
                mock.patch.object(post_pr_review, "request_reviewer") as request_reviewer,
                mock.patch(
                    "sys.argv",
                    ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)],
                ),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_json.assert_not_called()
        request_reviewer.assert_called_once_with("owner/repo", "token", 5, "owner")

    def test_main_does_not_request_reviewer_for_non_member_approved_spec_only_pr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "APPROVE", "body": "summary", "comments": []}),
                encoding="utf-8",
            )
            diff_path.write_text(
                "\n".join(["# PR_DIFF_V1", "FILE specs/issue-1/product.md", "END_FILE", ""]),
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "NONE",
                            "user": {"login": "external", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(post_pr_review, "parse_codeowners", return_value=[post_pr_review.CodeownersRule("*", ["@owner"])]),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}) as request_json,
                mock.patch.object(post_pr_review, "request_reviewer") as request_reviewer,
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
                "comments": [],
            },
        )
        request_reviewer.assert_not_called()

    def test_main_skips_reviewer_request_when_codeowners_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            diff_path = Path(directory) / "pr_diff.txt"
            review_path.write_text(
                json.dumps({"verdict": "APPROVE", "body": "summary", "comments": []}),
                encoding="utf-8",
            )
            diff_path.write_text(
                "\n".join(["# PR_DIFF_V1", "FILE app.py", "END_FILE", ""]),
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
                    return_value={
                        "pull_request": {
                            "number": 5,
                            "head": {"sha": "abc123"},
                            "author_association": "NONE",
                            "user": {"login": "external", "type": "User"},
                        }
                    },
                ),
                mock.patch.object(post_pr_review, "parse_codeowners", return_value=[]),
                mock.patch.object(post_pr_review, "request_json", return_value={"id": 99}),
                mock.patch.object(post_pr_review, "list_pull_request_reviews", return_value=[]),
                mock.patch.object(post_pr_review, "request_reviewer") as request_reviewer,
                mock.patch(
                    "sys.argv",
                    ["post_pr_review.py", "--review", str(review_path), "--diff", str(diff_path)],
                ),
                mock.patch("builtins.print"),
            ):
                post_pr_review.main()

        request_reviewer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
