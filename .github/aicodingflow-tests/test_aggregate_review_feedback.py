from __future__ import annotations

import unittest

from script_imports import import_script


aggregate = import_script(
    ".github/skills/update-pr-review/scripts/aggregate_review_feedback.py",
    "aggregate_review_feedback",
)


class AggregateReviewFeedbackTest(unittest.TestCase):
    def test_default_agent_logins_cover_github_actions_names(self) -> None:
        self.assertIn("github-actions", aggregate.DEFAULT_AGENT_LOGINS)
        self.assertIn("github-actions[bot]", aggregate.DEFAULT_AGENT_LOGINS)

    def test_agent_login_set_adds_to_defaults(self) -> None:
        self.assertEqual(
            aggregate.agent_login_set(["oz-bot"]),
            {"github-actions", "github-actions[bot]", "oz-bot"},
        )

    def test_default_agent_logins_stay_excluded_when_bots_are_included(self) -> None:
        comment = {"author": {"__typename": "Bot", "login": "github-actions"}}
        self.assertFalse(aggregate.is_human_comment(comment, aggregate.agent_login_set(["oz-bot"]), True))

    def test_classify_spec_only_files(self) -> None:
        self.assertEqual(aggregate.classify_review_type(["specs/a.md", "specs/nested/b.md"]), "spec")

    def test_classify_mixed_files_as_code(self) -> None:
        self.assertEqual(aggregate.classify_review_type(["specs/a.md", "src/app.py"]), "code")

    def test_detects_severity_and_suggestion_blocks(self) -> None:
        body = "⚠️ [IMPORTANT] tighten this\n```suggestion\nx\n```"
        self.assertEqual(aggregate.severity(body), "IMPORTANT")
        self.assertTrue(aggregate.has_suggestion(body))

    def test_human_comment_excludes_missing_login(self) -> None:
        self.assertFalse(aggregate.is_human_comment({"author": None}, {"github-actions[bot]"}, False))

    def test_human_comment_excludes_agent_login(self) -> None:
        comment = {"author": {"__typename": "User", "login": "github-actions[bot]"}}
        self.assertFalse(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))

    def test_human_comment_excludes_other_bots_by_default(self) -> None:
        comment = {"author": {"__typename": "Bot", "login": "copilot-pull-request-reviewer[bot]"}}
        self.assertFalse(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))

    def test_human_comment_can_include_other_bots(self) -> None:
        comment = {"author": {"__typename": "Bot", "login": "copilot-pull-request-reviewer[bot]"}}
        self.assertTrue(aggregate.is_human_comment(comment, {"github-actions[bot]"}, True))

    def test_human_comment_includes_non_agent_user(self) -> None:
        comment = {"author": {"__typename": "User", "login": "maintainer"}}
        self.assertTrue(aggregate.is_human_comment(comment, {"github-actions[bot]"}, False))

    def test_paginate_pull_request_connection_fetches_remaining_pages(self) -> None:
        pr = {
            "files": {
                "nodes": [{"path": "a.py"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            }
        }
        calls = []

        def fake_run_graphql(query, variables):
            calls.append((query, variables))
            return {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "files": {
                                "nodes": [{"path": "b.py"}],
                                "pageInfo": {"hasNextPage": False, "endCursor": "cursor-2"},
                            }
                        }
                    }
                }
            }

        original = aggregate.run_graphql
        aggregate.run_graphql = fake_run_graphql
        try:
            aggregate.paginate_pull_request_connection("owner", "repo", 1, pr, "files", "path")
        finally:
            aggregate.run_graphql = original

        self.assertEqual([node["path"] for node in pr["files"]["nodes"]], ["a.py", "b.py"])
        self.assertEqual(calls[0][1]["after"], "cursor-1")

    def test_paginate_thread_comments_fetches_remaining_pages(self) -> None:
        thread = {
            "id": "thread-1",
            "comments": {
                "nodes": [{"body": "first"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            },
        }

        def fake_run_graphql(query, variables):
            return {
                "data": {
                    "node": {
                        "comments": {
                            "nodes": [{"body": "second"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": "cursor-2"},
                        }
                    }
                }
            }

        original = aggregate.run_graphql
        aggregate.run_graphql = fake_run_graphql
        try:
            aggregate.paginate_thread_comments(thread)
        finally:
            aggregate.run_graphql = original

        self.assertEqual([comment["body"] for comment in thread["comments"]["nodes"]], ["first", "second"])

    def test_paginate_review_comments_fetches_remaining_pages(self) -> None:
        review = {
            "id": "review-1",
            "comments": {
                "nodes": [{"body": "first"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            },
        }

        def fake_run_graphql(query, variables):
            return {
                "data": {
                    "node": {
                        "comments": {
                            "nodes": [{"body": "second"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": "cursor-2"},
                        }
                    }
                }
            }

        original = aggregate.run_graphql
        aggregate.run_graphql = fake_run_graphql
        try:
            aggregate.paginate_review_comments(review)
        finally:
            aggregate.run_graphql = original

        self.assertEqual([comment["body"] for comment in review["comments"]["nodes"]], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
