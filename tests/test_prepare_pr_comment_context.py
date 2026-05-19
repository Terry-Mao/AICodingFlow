from __future__ import annotations

import unittest
from unittest import mock

from tests.script_imports import import_script


prepare = import_script(".github/scripts/prepare_pr_comment_context.py", "prepare_pr_comment_context")


def pr_payload(*, number: int = 42, head_repo: str = "owner/repo", state: str = "open") -> dict:
    return {
        "number": number,
        "state": state,
        "title": "Fix parser",
        "body": "Refs #28",
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "maintainer_can_modify": True,
        "base": {"ref": "main", "sha": "base", "repo": {"full_name": "owner/repo"}},
        "head": {"ref": "feature", "sha": "head", "repo": {"full_name": head_repo}},
    }


def issue_comment_event(*, body: str = "@codex /fix", association: str = "MEMBER") -> dict:
    return {
        "issue": {"number": 42, "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/42"}},
        "comment": {
            "id": 1001,
            "body": body,
            "author_association": association,
            "user": {"login": "alice"},
            "created_at": "2026-05-17T00:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/42#issuecomment-1001",
        },
    }


def review_comment_event(*, body: str = "@codex /fix", association: str = "OWNER") -> dict:
    return {
        "pull_request": {"number": 42},
        "comment": {
            "id": 2002,
            "body": body,
            "author_association": association,
            "user": {"login": "bob"},
            "created_at": "2026-05-17T00:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/42#discussion_r2002",
        },
    }


def review_body_event(*, body: str = "@codex /fix", association: str = "COLLABORATOR") -> dict:
    return {
        "pull_request": {"number": 42},
        "review": {
            "id": 3003,
            "body": body,
            "author_association": association,
            "user": {"login": "carol"},
            "submitted_at": "2026-05-17T00:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/42#pullrequestreview-3003",
        },
    }


class PreparePrCommentContextTest(unittest.TestCase):
    def build_context(self, event_name: str, event: dict, pr: dict | None = None) -> dict:
        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr or pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
        ):
            context, _ = prepare.build_context("owner/repo", event_name, event, "codex")
        return context

    def test_issue_comment_happy_path_uses_push_head_for_same_repo(self) -> None:
        context = self.build_context("issue_comment", issue_comment_event(body="@codex /fix update the docs"))

        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_kind"], "conversation")
        self.assertEqual(context["trigger_comment_id"], 1001)
        self.assertEqual(context["trigger_body"], "@codex /fix update the docs")
        self.assertEqual(context["trigger_actor_association"], "MEMBER")
        self.assertTrue(context["trigger_actor_is_authorized"])
        self.assertEqual(context["branch_strategy"], "push-head")
        self.assertEqual(context["agent_push_branch"], "feature")

    def test_review_comment_records_reply_target(self) -> None:
        context = self.build_context("pull_request_review_comment", review_comment_event(body="@codex /fix please remove this"))

        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_kind"], "review")
        self.assertEqual(context["review_reply_target_id"], 2002)
        self.assertEqual(context["trigger_body"], "@codex /fix please remove this")

    def test_review_body_happy_path(self) -> None:
        context = self.build_context("pull_request_review", review_body_event(body="@codex /fix address requested changes"))

        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_kind"], "review_body")
        self.assertEqual(context["trigger_comment_id"], 3003)
        self.assertEqual(context["trigger_body"], "@codex /fix address requested changes")

    def test_untrusted_actor_is_hard_skipped(self) -> None:
        context = self.build_context("issue_comment", issue_comment_event(association="CONTRIBUTOR"))

        self.assertFalse(context["should_run"])
        self.assertFalse(context["trigger_actor_is_authorized"])
        self.assertIn("not authorized", context["skip_reason"])

    def test_missing_fix_command_is_skipped(self) -> None:
        context = self.build_context("issue_comment", issue_comment_event(body="@codex /review"))

        self.assertFalse(context["should_run"])
        self.assertIn("missing valid", context["skip_reason"])

    def test_fork_pr_uses_fallback_branch(self) -> None:
        context = self.build_context(
            "issue_comment",
            issue_comment_event(),
            pr=pr_payload(head_repo="fork/repo"),
        )

        self.assertTrue(context["should_run"])
        self.assertEqual(context["branch_strategy"], "fallback-pr-to-fork")
        self.assertEqual(context["agent_push_branch"], "spec/respond-pr-42")

    def test_review_comment_index_keeps_numeric_ids(self) -> None:
        index = prepare.review_comment_index(
            [
                {
                    "id": 11,
                    "pull_request_review_id": 9,
                    "path": "app.py",
                    "line": 3,
                    "body": "Please fix this branch.",
                    "diff_hunk": "@@ -1,3 +1,3 @@",
                    "html_url": "https://github.com/owner/repo/pull/42#discussion_r11",
                    "author_association": "MEMBER",
                    "user": {"login": "alice"},
                }
            ]
        )

        self.assertEqual(index["review_comments"][0]["comment_id"], 11)
        self.assertEqual(index["review_comments"][0]["path"], "app.py")
        self.assertEqual(index["review_comments"][0]["body"], "Please fix this branch.")
        self.assertEqual(index["review_comments"][0]["diff_hunk"], "@@ -1,3 +1,3 @@")
        self.assertEqual(index["review_comments"][0]["url"], "https://github.com/owner/repo/pull/42#discussion_r11")


if __name__ == "__main__":
    unittest.main()
