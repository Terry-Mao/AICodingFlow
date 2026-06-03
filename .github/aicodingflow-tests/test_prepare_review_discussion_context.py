from __future__ import annotations

import unittest

from script_imports import import_script


prepare = import_script(".github/scripts/prepare_review_discussion_context.py", "prepare_review_discussion_context")


class PrepareReviewDiscussionContextTest(unittest.TestCase):
    def test_build_context_suppresses_resolved_and_dismissed_bot_comments(self) -> None:
        comments = [
            {
                "id": 11,
                "path": "app.py",
                "line": 3,
                "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                "diff_hunk": "@@ -1,3 +1,3 @@",
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r11",
                "author_association": "NONE",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            },
            {
                "id": 12,
                "in_reply_to_id": 11,
                "body": "不用改，这是预期行为。",
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r12",
                "author_association": "MEMBER",
                "user": {"login": "maintainer", "type": "User"},
            },
            {
                "id": 21,
                "path": "app.py",
                "line": 9,
                "body": "⚠️ [IMPORTANT] This branch can still fail.",
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r21",
                "author_association": "NONE",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            },
            {
                "id": 31,
                "path": "app.py",
                "line": 14,
                "body": "⚠️ [IMPORTANT] Validate this edge case.",
                "html_url": "https://github.com/owner/repo/pull/42#discussion_r31",
                "author_association": "NONE",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            },
        ]
        threads = [
            {
                "id": "thread-11",
                "isResolved": False,
                "isOutdated": False,
                "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
            },
            {
                "id": "thread-21",
                "isResolved": True,
                "isOutdated": False,
                "comments": {"nodes": [{"databaseId": 21}]},
            },
            {
                "id": "thread-31",
                "isResolved": False,
                "isOutdated": True,
                "comments": {"nodes": [{"databaseId": 31}]},
            },
        ]

        context = prepare.build_review_discussion_context(comments, threads)

        suppressed = context["suppressed_review_comments"]
        unresolved = context["unresolved_review_comments"]
        self.assertEqual([item["comment_id"] for item in suppressed], [11, 21])
        self.assertEqual(suppressed[0]["reason"], "maintainer_dismissed")
        self.assertEqual(suppressed[0]["maintainer_reply"]["author"], "maintainer")
        self.assertEqual(suppressed[0]["authorized_replies"][0]["body"], "不用改，这是预期行为。")
        self.assertEqual(suppressed[1]["reason"], "thread_resolved")
        self.assertEqual([item["comment_id"] for item in unresolved], [31])
        self.assertTrue(unresolved[0]["is_outdated"])

    def test_non_maintainer_dismissal_reply_does_not_suppress(self) -> None:
        context = prepare.build_review_discussion_context(
            [
                {
                    "id": 11,
                    "path": "app.py",
                    "line": 3,
                    "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                    "author_association": "NONE",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                },
                {
                    "id": 12,
                    "in_reply_to_id": 11,
                    "body": "no need to fix this",
                    "author_association": "CONTRIBUTOR",
                    "user": {"login": "external", "type": "User"},
                },
            ],
            [
                {
                    "id": "thread-11",
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
                }
            ],
        )

        self.assertEqual(context["suppressed_review_comments"], [])
        self.assertEqual(context["unresolved_review_comments"][0]["comment_id"], 11)

    def test_authorized_bare_no_need_reply_suppresses(self) -> None:
        context = prepare.build_review_discussion_context(
            [
                {
                    "id": 11,
                    "path": "app.py",
                    "line": 3,
                    "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                    "author_association": "NONE",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                },
                {
                    "id": 12,
                    "in_reply_to_id": 11,
                    "body": "No need.",
                    "author_association": "MEMBER",
                    "user": {"login": "maintainer", "type": "User"},
                },
            ],
            [
                {
                    "id": "thread-11",
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
                }
            ],
        )

        self.assertEqual(context["suppressed_review_comments"][0]["comment_id"], 11)
        self.assertEqual(context["suppressed_review_comments"][0]["reason"], "maintainer_dismissed")
        self.assertEqual(context["unresolved_review_comments"], [])

    def test_intentional_in_negative_or_question_context_does_not_suppress(self) -> None:
        for reply_body in (
            "this is not intentional",
            "is this intentional?",
            "this is not an intentional change",
            "is this an intentional change?",
        ):
            with self.subTest(reply_body=reply_body):
                context = prepare.build_review_discussion_context(
                    [
                        {
                            "id": 11,
                            "path": "app.py",
                            "line": 3,
                            "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                            "author_association": "NONE",
                            "user": {"login": "github-actions[bot]", "type": "Bot"},
                        },
                        {
                            "id": 12,
                            "in_reply_to_id": 11,
                            "body": reply_body,
                            "author_association": "MEMBER",
                            "user": {"login": "maintainer", "type": "User"},
                        },
                    ],
                    [
                        {
                            "id": "thread-11",
                            "isResolved": False,
                            "isOutdated": False,
                            "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
                        }
                    ],
                )

                self.assertEqual(context["suppressed_review_comments"], [])
                self.assertEqual(context["unresolved_review_comments"][0]["comment_id"], 11)

    def test_other_bot_comments_are_not_treated_as_review_bot_feedback(self) -> None:
        context = prepare.build_review_discussion_context(
            [
                {
                    "id": 11,
                    "path": "app.py",
                    "line": 3,
                    "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                    "author_association": "NONE",
                    "user": {"login": "other-review-bot[bot]", "type": "Bot"},
                },
                {
                    "id": 12,
                    "in_reply_to_id": 11,
                    "body": "no need to fix this",
                    "author_association": "MEMBER",
                    "user": {"login": "maintainer", "type": "User"},
                },
            ],
            [
                {
                    "id": "thread-11",
                    "isResolved": True,
                    "isOutdated": False,
                    "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
                }
            ],
            bot_login="github-actions[bot]",
        )

        self.assertEqual(context["suppressed_review_comments"], [])
        self.assertEqual(context["unresolved_review_comments"], [])

    def test_unmatched_authorized_reply_is_still_available_for_model_judgment(self) -> None:
        context = prepare.build_review_discussion_context(
            [
                {
                    "id": 11,
                    "path": "app.py",
                    "line": 3,
                    "body": "⚠️ [IMPORTANT] Please handle missing fallback.",
                    "author_association": "NONE",
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                },
                {
                    "id": 12,
                    "in_reply_to_id": 11,
                    "body": "这里先保留现在的行为，后续再看。",
                    "author_association": "OWNER",
                    "user": {"login": "maintainer", "type": "User"},
                },
            ],
            [
                {
                    "id": "thread-11",
                    "isResolved": False,
                    "isOutdated": False,
                    "comments": {"nodes": [{"databaseId": 11}, {"databaseId": 12}]},
                }
            ],
        )

        self.assertEqual(context["suppressed_review_comments"], [])
        self.assertEqual(context["unresolved_review_comments"][0]["comment_id"], 11)
        self.assertEqual(context["unresolved_review_comments"][0]["authorized_replies"][0]["author"], "maintainer")
        self.assertIn("保留现在的行为", context["unresolved_review_comments"][0]["authorized_replies"][0]["body"])


if __name__ == "__main__":
    unittest.main()
