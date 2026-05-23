from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from script_imports import import_script


prepare = import_script(".github/scripts/prepare_pr_comment_context.py", "prepare_pr_comment_context")


def pr_payload(*, number: int = 42, head_repo: str = "owner/repo", state: str = "open", private: bool = False) -> dict:
    return {
        "number": number,
        "state": state,
        "title": "Fix parser",
        "body": "Refs #28",
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "maintainer_can_modify": True,
        "base": {"ref": "main", "sha": "base", "repo": {"full_name": "owner/repo", "private": private}},
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
    def build_context(self, event_name: str, event: dict, pr: dict | None = None, permission: str = "") -> dict:
        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr or pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
            mock.patch.object(prepare, "fetch_collaborator_permission", return_value=permission),
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

    def test_issue_comment_falls_back_to_api_for_none_author_association(self) -> None:
        event = issue_comment_event(association="NONE")

        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
            mock.patch.object(
                prepare,
                "fetch_trigger_item",
                return_value={"author_association": "MEMBER", "user": {"login": "alice"}},
            ) as fetch_trigger_item,
        ):
            context, _ = prepare.build_context("owner/repo", "issue_comment", event, "codex")

        fetch_trigger_item.assert_called_once()
        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_actor_association"], "MEMBER")

    def test_review_comment_falls_back_to_api_for_none_author_association(self) -> None:
        event = review_comment_event(association="NONE")

        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
            mock.patch.object(
                prepare,
                "fetch_trigger_item",
                return_value={"author_association": "OWNER", "user": {"login": "bob"}},
            ) as fetch_trigger_item,
        ):
            context, _ = prepare.build_context("owner/repo", "pull_request_review_comment", event, "codex")

        fetch_trigger_item.assert_called_once()
        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_actor_association"], "OWNER")

    def test_review_body_falls_back_to_api_for_none_author_association(self) -> None:
        event = review_body_event(association="NONE")

        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
            mock.patch.object(
                prepare,
                "fetch_trigger_item",
                return_value={"author_association": "COLLABORATOR", "user": {"login": "carol"}},
            ) as fetch_trigger_item,
        ):
            context, _ = prepare.build_context("owner/repo", "pull_request_review", event, "codex")

        fetch_trigger_item.assert_called_once()
        self.assertTrue(context["should_run"])
        self.assertEqual(context["trigger_actor_association"], "COLLABORATOR")

    def test_public_contributor_is_hard_skipped_without_permission_lookup(self) -> None:
        with (
            mock.patch.object(prepare, "fetch_pr", return_value=pr_payload()),
            mock.patch.object(prepare, "fetch_default_branch", return_value="main"),
            mock.patch.object(prepare, "fetch_collaborator_permission") as fetch_permission,
        ):
            context, _ = prepare.build_context(
                "owner/repo",
                "issue_comment",
                issue_comment_event(association="CONTRIBUTOR"),
                "codex",
            )

        fetch_permission.assert_not_called()
        self.assertFalse(context["should_run"])
        self.assertFalse(context["trigger_actor_is_authorized"])
        self.assertFalse(context["base_repo_private"])
        self.assertEqual(context["trigger_actor_repository_permission"], "")
        self.assertIn("public repositories", context["skip_reason"])

    def test_private_contributor_with_write_permission_is_authorized(self) -> None:
        context = self.build_context(
            "issue_comment",
            issue_comment_event(association="CONTRIBUTOR"),
            pr=pr_payload(private=True),
            permission="write",
        )

        self.assertTrue(context["should_run"])
        self.assertTrue(context["trigger_actor_is_authorized"])
        self.assertTrue(context["base_repo_private"])
        self.assertEqual(context["trigger_actor_repository_permission"], "write")
        self.assertEqual(context["skip_reason"], "")

    def test_private_contributor_with_read_permission_is_skipped(self) -> None:
        context = self.build_context(
            "issue_comment",
            issue_comment_event(association="CONTRIBUTOR"),
            pr=pr_payload(private=True),
            permission="read",
        )

        self.assertFalse(context["should_run"])
        self.assertFalse(context["trigger_actor_is_authorized"])
        self.assertTrue(context["base_repo_private"])
        self.assertEqual(context["trigger_actor_repository_permission"], "read")
        self.assertIn("not write/maintain/admin", context["skip_reason"])

    def test_private_contributor_permission_lookup_failure_is_skipped(self) -> None:
        with mock.patch.object(
            prepare,
            "run_gh_json",
            side_effect=subprocess.CalledProcessError(1, ["gh", "api"]),
        ):
            permission = prepare.fetch_collaborator_permission("owner/repo", "alice")

        self.assertEqual(permission, "")

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
            ],
            [
                {
                    "id": "thread-node-1",
                    "isResolved": False,
                    "isOutdated": True,
                    "comments": {"nodes": [{"databaseId": 11}]},
                }
            ]
        )

        self.assertEqual(index["review_comments"][0]["comment_id"], 11)
        self.assertEqual(index["review_comments"][0]["review_thread_node_id"], "thread-node-1")
        self.assertFalse(index["review_comments"][0]["is_resolved"])
        self.assertTrue(index["review_comments"][0]["is_outdated"])
        self.assertEqual(index["review_comments"][0]["path"], "app.py")
        self.assertEqual(index["review_comments"][0]["body"], "Please fix this branch.")
        self.assertEqual(index["review_comments"][0]["diff_hunk"], "@@ -1,3 +1,3 @@")
        self.assertEqual(index["review_comments"][0]["url"], "https://github.com/owner/repo/pull/42#discussion_r11")


if __name__ == "__main__":
    unittest.main()
