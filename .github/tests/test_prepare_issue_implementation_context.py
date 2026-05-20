from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


prepare_impl = import_script(
    ".github/scripts/prepare_issue_implementation_context.py",
    "prepare_issue_implementation_context",
)


class PrepareIssueImplementationContextTest(unittest.TestCase):
    def test_implementation_target_branch_uses_issue_number(self) -> None:
        self.assertEqual(prepare_impl.implementation_target_branch(18), "spec/implement-issue-18")

    def test_should_run_when_ready_label_is_added_to_assigned_issue(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            agent_login="codex[bot]",
        )
        event = {"action": "labeled", "label": {"name": "ready-to-implement"}}
        issue = {
            "labels": [{"name": "ready-to-implement"}],
            "assignees": [{"login": "codex[bot]"}],
        }

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (True, "ready-to-implement label added to issue assigned to codex[bot]"),
        )

    def test_should_not_run_for_unrelated_issue_label_event(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            agent_login="codex",
        )
        event = {"action": "labeled", "label": {"name": "bug"}}
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": [{"login": "codex"}]}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (False, "issue label event is not ready-to-implement"),
        )

    def test_should_run_when_agent_is_assigned_to_ready_issue(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            agent_login="codex",
        )
        event = {"action": "assigned", "assignee": {"login": "codex"}}
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": [{"login": "codex"}]}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (True, "ready-to-implement issue assigned to codex"),
        )

    def test_should_not_run_when_issue_assignment_is_for_someone_else(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            agent_login="codex",
        )
        event = {"action": "assigned", "assignee": {"login": "alice"}}
        issue = {
            "labels": [{"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}, {"login": "alice"}],
        }

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (False, "issue assignment event is not for codex"),
        )

    def test_should_not_run_for_reopened_ready_assigned_issue(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            agent_login="codex",
        )
        event = {"action": "reopened"}
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": [{"login": "codex"}]}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (False, "issue event action is not an implementation trigger: reopened"),
        )

    def test_workflow_dispatch_still_requires_ready_label_and_assignment(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="workflow_dispatch",
            agent_login="codex",
        )

        self.assertEqual(
            prepare_impl.should_run(args, {}, {"labels": [], "assignees": [{"login": "codex"}]}),
            (False, "issue is missing ready-to-implement"),
        )
        self.assertEqual(
            prepare_impl.should_run(
                args,
                {},
                {"labels": [{"name": "ready-to-implement"}], "assignees": []},
            ),
            (False, "ready-to-implement issue is not assigned to or mentioning the configured agent"),
        )
        self.assertEqual(
            prepare_impl.should_run(
                args,
                {},
                {"labels": [{"name": "ready-to-implement"}], "assignees": [{"login": "codex"}]},
            ),
            (True, "ready-to-implement assigned to codex"),
        )

    def test_should_run_for_ready_to_implement_comment_mention(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issue_comment",
            agent_login="codex",
        )
        event = {"comment": {"body": "@codex please implement this"}}
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": []}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (True, "ready-to-implement comment mentioned @codex"),
        )

    def test_should_not_run_for_pull_request_comment_mention(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issue_comment",
            agent_login="codex",
        )
        event = {
            "issue": {"pull_request": {"url": "https://api.github.test/repos/owner/repo/pulls/61"}},
            "comment": {"body": "@codex please implement this"},
        }
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": []}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (False, "PR comments are handled by review-pr workflow"),
        )

    def test_should_not_run_for_partial_or_quoted_agent_mention(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issue_comment",
            agent_login="codex",
        )
        event = {"comment": {"body": "@codex-action should handle this\n> @codex old text"}}
        issue = {"labels": [{"name": "ready-to-implement"}], "assignees": []}

        self.assertEqual(
            prepare_impl.should_run(args, event, issue),
            (False, "ready-to-implement issue is not assigned to or mentioning the configured agent"),
        )

    def test_resolves_approved_spec_pr_before_directory(self) -> None:
        spec_pr = {
            "number": 123,
            "html_url": "https://github.test/owner/repo/pull/123",
            "updated_at": "2026-05-13T10:20:30Z",
            "labels": [{"name": "plan-approved"}],
            "head": {"ref": "spec/issue-18", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(prepare_impl, "fetch_spec_prs", return_value=[spec_pr]),
            mock.patch.object(
                prepare_impl,
                "collect_spec_entries",
                return_value=[
                    {"path": "specs/issue-18/product.md", "content": "# Product\n"},
                    {"path": "specs/issue-18/tech.md", "content": "# Tech\n"},
                ],
            ) as collect_spec_entries,
        ):
            context = prepare_impl.resolve_implementation_spec_context("owner/repo", 18, "main")

        self.assertEqual(context["spec_context_source"], "approved-pr")
        self.assertEqual(context["selected_spec_pr"]["number"], 123)
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-18/product.md", "specs/issue-18/tech.md"],
            "spec/issue-18",
        )

    def test_falls_back_to_directory_when_no_approved_pr(self) -> None:
        unapproved = {
            "number": 122,
            "html_url": "https://github.test/owner/repo/pull/122",
            "updated_at": "2026-05-12T10:20:30Z",
            "labels": [],
            "head": {"ref": "spec/issue-18", "repo": {"full_name": "owner/repo"}},
        }

        with (
            mock.patch.object(prepare_impl, "fetch_spec_prs", return_value=[unapproved]),
            mock.patch.object(
                prepare_impl,
                "collect_spec_entries",
                return_value=[{"path": "specs/issue-18/product.md", "content": "# Product\n"}],
            ) as collect_spec_entries,
        ):
            context = prepare_impl.resolve_implementation_spec_context("owner/repo", 18, "main")

        self.assertEqual(context["spec_context_source"], "directory")
        self.assertEqual(context["unapproved_spec_prs"][0]["number"], 122)
        collect_spec_entries.assert_called_once_with(
            "owner/repo",
            ["specs/issue-18/product.md", "specs/issue-18/tech.md"],
            "main",
        )

    def test_main_sets_noop_for_unapproved_spec_pr_without_directory_specs(self) -> None:
        issue = {
            "number": 18,
            "title": "Implement issue",
            "body": "",
            "author": {"login": "maintainer"},
            "labels": [{"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}],
            "url": "https://github.test/owner/repo/issues/18",
        }
        spec_pr = {
            "number": 122,
            "html_url": "https://github.test/owner/repo/pull/122",
            "updated_at": "2026-05-12T10:20:30Z",
            "labels": [],
            "head": {"ref": "spec/issue-18", "repo": {"full_name": "owner/repo"}},
        }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "issue_context.json"
            comments_output = Path(directory) / "issue_comments.txt"
            spec_output = Path(directory) / "spec_context.md"
            github_output = Path(directory) / "github_output.txt"
            with (
                mock.patch.object(prepare_impl, "fetch_issue", return_value=issue),
                mock.patch.object(prepare_impl, "fetch_comments", return_value=[]),
                mock.patch.object(prepare_impl, "fetch_default_branch", return_value="main"),
                mock.patch.object(prepare_impl, "fetch_spec_prs", return_value=[spec_pr]),
                mock.patch.object(prepare_impl, "collect_spec_entries", return_value=[]),
                mock.patch.object(prepare_impl, "has_existing_implementation_pr", return_value=False),
                mock.patch.object(prepare_impl, "best_effort_assign", return_value=""),
                mock.patch(
                    "sys.argv",
                    [
                        "prepare_issue_implementation_context.py",
                        "--repo",
                        "owner/repo",
                        "--issue",
                        "18",
                        "--event-name",
                        "issues",
                        "--agent-login",
                        "codex",
                        "--output",
                        str(output),
                        "--comments-output",
                        str(comments_output),
                        "--spec-context-output",
                        str(spec_output),
                        "--github-output",
                        str(github_output),
                    ],
                ),
            ):
                prepare_impl.main()

            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(context["should_noop"])
            self.assertIn("none are labeled plan-approved", context["noop_reason"])
            self.assertEqual(context["spec_context_text"], "")
            self.assertFalse(spec_output.exists())

    def test_main_writes_spec_context_text_and_file_when_specs_exist(self) -> None:
        issue = {
            "number": 18,
            "title": "Implement issue",
            "body": "",
            "author": {"login": "maintainer"},
            "labels": [{"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}],
            "url": "https://github.test/owner/repo/issues/18",
        }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "issue_context.json"
            comments_output = Path(directory) / "issue_comments.txt"
            spec_output = Path(directory) / "spec_context.md"
            github_output = Path(directory) / "github_output.txt"
            with (
                mock.patch.object(prepare_impl, "fetch_issue", return_value=issue),
                mock.patch.object(prepare_impl, "fetch_comments", return_value=[]),
                mock.patch.object(prepare_impl, "fetch_default_branch", return_value="main"),
                mock.patch.object(prepare_impl, "fetch_spec_prs", return_value=[]),
                mock.patch.object(
                    prepare_impl,
                    "collect_spec_entries",
                    return_value=[{"path": "specs/issue-18/product.md", "content": "# Product\n"}],
                ),
                mock.patch.object(prepare_impl, "has_existing_implementation_pr", return_value=False),
                mock.patch.object(prepare_impl, "best_effort_assign", return_value=""),
                mock.patch(
                    "sys.argv",
                    [
                        "prepare_issue_implementation_context.py",
                        "--repo",
                        "owner/repo",
                        "--issue",
                        "18",
                        "--event-name",
                        "issues",
                        "--agent-login",
                        "codex",
                        "--output",
                        str(output),
                        "--comments-output",
                        str(comments_output),
                        "--spec-context-output",
                        str(spec_output),
                        "--github-output",
                        str(github_output),
                    ],
                ),
            ):
                prepare_impl.main()

            context = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(context["spec_context_source"], "directory")
            self.assertIn("Repository spec context was found in `specs/`.", context["spec_context_text"])
            self.assertEqual(spec_output.read_text(encoding="utf-8"), context["spec_context_text"])


if __name__ == "__main__":
    unittest.main()
