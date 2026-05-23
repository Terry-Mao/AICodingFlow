from __future__ import annotations

import unittest
from unittest import mock

from script_imports import import_script


apply_result = import_script(".github/scripts/apply_pr_comment_result.py", "apply_pr_comment_result")


class ApplyPrCommentResultTest(unittest.TestCase):
    def test_push_head_updates_original_pr_and_replies(self) -> None:
        calls: list[tuple[str, object]] = []
        context = {"branch_strategy": "push-head", "pr_number": 42}
        metadata = {
            "branch_name": "feature",
            "pr_title": "fix: update parser",
            "pr_summary": "Refs #42\n\nBody",
        }

        with (
            mock.patch.object(apply_result, "update_original_pr", side_effect=lambda *args: calls.append(("update", args)) or "https://pr/42"),
            mock.patch.object(apply_result, "reply_to_issue_comment", side_effect=lambda *args: calls.append(("reply", args))),
        ):
            result = apply_result.apply_result("owner/repo", context, metadata, {})

        self.assertEqual(result["pr_url"], "https://pr/42")
        self.assertEqual(calls[0][0], "update")
        self.assertEqual(calls[1][0], "reply")
        self.assertEqual(
            calls[1][1],
            (
                "owner/repo",
                42,
                "Applied requested changes on `feature`.\n\nSummary:\nBody\n\nhttps://pr/42",
            ),
        )

    def test_update_original_pr_does_not_edit_title_or_body(self) -> None:
        gh_calls: list[list[str]] = []
        metadata = {
            "branch_name": "feature",
            "pr_title": "fix: update parser",
            "pr_summary": "Refs #42\n\nBody",
        }

        with (
            mock.patch.object(apply_result, "run_gh", side_effect=lambda args, **_: gh_calls.append(args) or ""),
            mock.patch.object(apply_result, "run_gh_json", return_value={"url": "https://pr/42"}),
        ):
            url = apply_result.update_original_pr("owner/repo", 42, metadata)

        self.assertEqual(url, "https://pr/42")
        self.assertEqual(gh_calls, [])

    def test_fallback_creates_followup_and_resolves_review_comments(self) -> None:
        calls: list[tuple[str, object]] = []
        context = {"branch_strategy": "fallback-pr-to-fork", "pr_number": 42, "base_branch": "main"}
        metadata = {
            "branch_name": "spec/respond-pr-42",
            "pr_title": "fix: update parser",
            "pr_summary": "Refs #42\n\nBody",
        }
        resolved = {"resolved_review_comments": [{"comment_id": 123, "summary": "Updated `app.py`."}]}

        with (
            mock.patch.object(apply_result, "create_or_update_followup_pr", side_effect=lambda *args: calls.append(("followup", args)) or "https://pr/99"),
            mock.patch.object(apply_result, "reply_to_issue_comment", side_effect=lambda *args: calls.append(("reply", args))),
            mock.patch.object(apply_result, "reply_to_review_comment", side_effect=lambda *args: calls.append(("review_reply", args))),
            mock.patch.object(apply_result, "resolve_thread_best_effort", side_effect=lambda *args: calls.append(("resolve", args)) or ""),
        ):
            result = apply_result.apply_result("owner/repo", context, metadata, resolved)

        self.assertEqual(result["pr_url"], "https://pr/99")
        self.assertEqual([name for name, _ in calls], ["followup", "reply", "review_reply", "resolve"])
        self.assertEqual(
            calls[1][1],
            (
                "owner/repo",
                42,
                "Applied requested changes on `spec/respond-pr-42`.\n\nSummary:\nBody\n\nhttps://pr/99",
            ),
        )
        self.assertEqual(calls[-2][1], ("owner/repo", 42, 123, "Updated `app.py`."))
        self.assertEqual(calls[-1][1], ("owner/repo", 42, 123))

    def test_issue_reply_body_omits_summary_when_pr_summary_is_empty(self) -> None:
        body = apply_result.issue_reply_body({"branch_name": "feature", "pr_summary": ""}, "https://pr/42")

        self.assertEqual(body, "Applied requested changes on `feature`.\n\nhttps://pr/42")

    def test_reply_to_review_comment_uses_pull_request_reply_endpoint(self) -> None:
        calls: list[list[str]] = []
        with mock.patch.object(apply_result, "run_gh", side_effect=lambda args, **_: calls.append(args)):
            apply_result.reply_to_review_comment("owner/repo", 42, 123, "Done.")

        self.assertEqual(
            calls,
            [["api", "repos/owner/repo/pulls/42/comments/123/replies", "-f", "body=Done."]],
        )

    def test_fetch_all_review_threads_paginates_threads_and_comments(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_run_graphql(query: str, variables: dict[str, object]) -> dict:
            calls.append(variables)
            if "prNumber" in variables and "after" not in variables:
                return {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "pageInfo": {"hasNextPage": True, "endCursor": "thread-cursor"},
                                    "nodes": [
                                        {
                                            "id": "thread-1",
                                            "isResolved": False,
                                            "comments": {
                                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                                "nodes": [{"databaseId": 111}],
                                            },
                                        }
                                    ],
                                }
                            }
                        }
                    }
                }
            if "prNumber" in variables and variables.get("after") == "thread-cursor":
                return {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                                    "nodes": [
                                        {
                                            "id": "thread-2",
                                            "isResolved": False,
                                            "comments": {
                                                "pageInfo": {"hasNextPage": True, "endCursor": "comment-cursor"},
                                                "nodes": [{"databaseId": 222}],
                                            },
                                        }
                                    ],
                                }
                            }
                        }
                    }
                }
            return {
                "data": {
                    "node": {
                        "comments": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [{"databaseId": 333}],
                        }
                    }
                }
            }

        with mock.patch.object(apply_result, "run_graphql", side_effect=fake_run_graphql):
            threads = apply_result.fetch_all_review_threads("owner/repo", 42)

        self.assertEqual([thread["id"] for thread in threads], ["thread-1", "thread-2"])
        self.assertEqual(threads[1]["comments"]["nodes"], [{"databaseId": 222}, {"databaseId": 333}])
        self.assertEqual(calls[-1], {"id": "thread-2", "after": "comment-cursor"})

    def test_resolve_thread_finds_comment_after_pagination(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        with (
            mock.patch.object(
                apply_result,
                "fetch_all_review_threads",
                return_value=[
                    {
                        "id": "thread-2",
                        "isResolved": False,
                        "comments": {"nodes": [{"databaseId": 333}]},
                    }
                ],
            ),
            mock.patch.object(apply_result, "run_graphql", side_effect=lambda query, variables: calls.append((query, variables)) or {}),
        ):
            warning = apply_result.resolve_thread_best_effort("owner/repo", 42, 333)

        self.assertEqual(warning, "")
        self.assertEqual(calls[-1][1], {"threadId": "thread-2"})


if __name__ == "__main__":
    unittest.main()
