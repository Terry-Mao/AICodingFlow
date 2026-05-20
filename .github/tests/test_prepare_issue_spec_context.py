#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


prepare_issue_spec_context = import_script(
    ".github/scripts/prepare_issue_spec_context.py",
    "prepare_issue_spec_context",
)


class PrepareIssueSpecContextTest(unittest.TestCase):
    def test_spec_paths_use_issue_directory_and_spec_branch(self) -> None:
        self.assertEqual(
            prepare_issue_spec_context.spec_paths(32),
            {
                "spec_dir": "specs/issue-32",
                "product_spec": "specs/issue-32/product.md",
                "tech_spec": "specs/issue-32/tech.md",
                "branch_name": "spec/issue-32",
                "target_branch": "spec/issue-32",
            },
        )

    def test_triggering_comment_extracts_stable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "comment": {
                            "body": "@codex please spec this",
                            "created_at": "2026-05-13T00:00:00Z",
                            "html_url": "https://github.test/comment",
                            "user": {"login": "maintainer"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                prepare_issue_spec_context.triggering_comment(str(event_path)),
                {
                    "id": None,
                    "author": "maintainer",
                    "body": "@codex please spec this",
                    "created_at": "2026-05-13T00:00:00Z",
                    "url": "https://github.test/comment",
                },
            )

    def test_remove_triggering_comment_filters_by_id_or_url(self) -> None:
        comments = [
            {"id": 1, "html_url": "https://github.test/one", "body": "old"},
            {"id": 2, "html_url": "https://github.test/two", "body": "trigger"},
            {"id": 3, "html_url": "https://github.test/three", "body": "later"},
        ]

        self.assertEqual(
            prepare_issue_spec_context.remove_triggering_comment(
                comments,
                {"id": 2, "url": "https://github.test/two"},
            ),
            [
                {"id": 1, "html_url": "https://github.test/one", "body": "old"},
                {"id": 3, "html_url": "https://github.test/three", "body": "later"},
            ],
        )

    def test_collect_coauthor_directives_deduplicates_valid_lines(self) -> None:
        self.assertEqual(
            prepare_issue_spec_context.collect_coauthor_directives(
                "Co-authored-by: Ada Lovelace <ada@example.com>",
                "text\nco-authored-by: Ada Lovelace <ada@example.com>\nCo-authored-by: Grace <grace@example.com>",
            ),
            [
                "Co-authored-by: Ada Lovelace <ada@example.com>",
                "Co-authored-by: Grace <grace@example.com>",
            ],
        )

    def test_should_run_when_ready_to_spec_label_is_added_to_assigned_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"action": "labeled", "label": {"name": "ready-to-spec"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex[bot]",
            )
            issue = {
                "labels": [{"name": "ready-to-spec"}],
                "assignees": [{"login": "codex[bot]"}],
            }

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec label added to issue assigned to codex[bot]"),
            )

    def test_should_not_run_for_unrelated_issue_label_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "labeled", "label": {"name": "bug"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue label event is not ready-to-spec"),
            )

    def test_should_run_when_agent_is_assigned_to_ready_to_spec_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "assigned", "assignee": {"login": "codex"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec issue assigned to codex"),
            )

    def test_should_not_run_when_issue_assignment_is_for_someone_else(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "assigned", "assignee": {"login": "alice"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {
                "labels": [{"name": "ready-to-spec"}],
                "assignees": [{"login": "codex"}, {"login": "alice"}],
            }

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue assignment event is not for codex"),
            )

    def test_should_not_run_for_reopened_ready_to_spec_assigned_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "reopened"}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue event action is not a spec trigger: reopened"),
            )

    def test_workflow_dispatch_still_requires_ready_label_and_assignment(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="workflow_dispatch",
            event_path="",
            agent_login="codex",
        )

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, {"labels": [], "assignees": [{"login": "codex"}]}),
            (False, "issue is missing ready-to-spec"),
        )
        self.assertEqual(
            prepare_issue_spec_context.should_run(
                args,
                {"labels": [{"name": "ready-to-spec"}], "assignees": []},
            ),
            (False, "ready-to-spec issue is not assigned to or mentioning the configured agent"),
        )
        self.assertEqual(
            prepare_issue_spec_context.should_run(
                args,
                {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]},
            ),
            (True, "ready-to-spec assigned to codex"),
        )

    def test_should_not_run_when_issue_is_already_ready_to_implement(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="codex",
        )
        issue = {
            "labels": [{"name": "ready-to-spec"}, {"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}],
        }

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "issue is already ready-to-implement"),
        )

    def test_should_run_for_ready_to_spec_comment_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"comment": {"body": "@codex please spec this"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec comment mentioned @codex"),
            )

    def test_should_not_run_for_pull_request_comment_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "issue": {"pull_request": {"url": "https://api.github.test/repos/owner/repo/pulls/61"}},
                        "comment": {"body": "@codex please spec this"},
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "PR comments are handled by review-pr workflow"),
            )

    def test_should_not_run_for_partial_or_quoted_agent_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"comment": {"body": "@codex-action should handle this\n> @codex old text"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "ready-to-spec issue is not assigned to or mentioning the configured agent"),
            )

    def test_comment_mentions_login_uses_login_boundaries(self) -> None:
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("please @codex.", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("please @codex[bot]", "codex[bot]"))
        self.assertFalse(prepare_issue_spec_context.comment_mentions_login("please @codex-action", "codex"))
        self.assertFalse(prepare_issue_spec_context.comment_mentions_login("> @codex quoted", "codex"))

    def test_should_not_run_without_ready_to_spec(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="codex[bot]",
        )
        issue = {"labels": [{"name": "enhancement"}], "assignees": [{"login": "codex[bot]"}]}

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "issue is missing ready-to-spec"),
        )

    def test_should_not_run_without_configured_agent_login(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="",
        )
        issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "agent login is not configured"),
        )


if __name__ == "__main__":
    unittest.main()
