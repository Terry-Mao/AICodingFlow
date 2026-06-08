from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


artifact_contracts = import_script(".github/scripts/artifact_contracts.py", "artifact_contracts")
context_snapshot = import_script(".github/scripts/context_snapshot.py", "context_snapshot")
github_event = import_script(".github/scripts/github_event.py", "github_event")


class ArtifactContractTests(unittest.TestCase):
    def test_load_and_write_json_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "artifact.json"
            artifact_contracts.write_json(path, {"message": "中文"})

            self.assertEqual(artifact_contracts.load_json(path), {"message": "中文"})
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_load_json_returns_default_for_missing_path(self) -> None:
        self.assertEqual(artifact_contracts.load_json("", default={}), {})
        self.assertEqual(artifact_contracts.load_json(None, default=[]), [])

    def test_write_github_output_appends_key_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "github_output.txt"

            artifact_contracts.write_github_output(path, {"should_run": "true", "reason": "ok"})
            artifact_contracts.write_github_output(path, {"issue_number": "243"})

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "should_run=true\nreason=ok\nissue_number=243\n",
            )


class GithubEventTests(unittest.TestCase):
    def test_extracts_stable_issue_fields(self) -> None:
        issue = {
            "labels": [{"name": "ready-to-spec"}, {"name": ""}, {}],
            "assignees": [{"login": "agent"}, {"login": ""}, {}],
        }

        self.assertEqual(github_event.label_names(issue), ["ready-to-spec"])
        self.assertEqual(github_event.assignee_logins(issue), ["agent"])

    def test_triggering_comment_snapshot_can_include_association(self) -> None:
        event = {
            "comment": {
                "id": 123,
                "user": {"login": "maintainer"},
                "author_association": "MEMBER",
                "body": "@agent /triage",
                "created_at": "2026-06-08T00:00:00Z",
                "html_url": "https://example.test/comment",
            }
        }

        self.assertEqual(
            github_event.triggering_comment_snapshot(event, include_author_association=True),
            {
                "id": 123,
                "author": "maintainer",
                "author_association": "MEMBER",
                "body": "@agent /triage",
                "created_at": "2026-06-08T00:00:00Z",
                "url": "https://example.test/comment",
            },
        )

    def test_detects_pull_request_issue_event_only_when_present(self) -> None:
        self.assertTrue(github_event.is_pull_request_issue_event({"issue": {"pull_request": {"url": "pr"}}}))
        self.assertFalse(github_event.is_pull_request_issue_event({"issue": {"pull_request": None}}))
        self.assertFalse(github_event.is_pull_request_issue_event({"issue": {}}))


class ContextSnapshotTests(unittest.TestCase):
    def test_flatten_pages_accepts_paginated_and_plain_lists(self) -> None:
        self.assertEqual(context_snapshot.flatten_pages([[{"id": 1}], [{"id": 2}]]), [{"id": 1}, {"id": 2}])
        self.assertEqual(context_snapshot.flatten_pages([{"id": 1}]), [{"id": 1}])

    def test_remove_triggering_comment_filters_by_id_or_url(self) -> None:
        comments = [
            {"id": 1, "html_url": "https://example.test/1"},
            {"id": 2, "html_url": "https://example.test/2"},
            {"id": 3, "html_url": "https://example.test/trigger"},
        ]

        self.assertEqual(
            context_snapshot.remove_triggering_comment(
                comments,
                {"id": 2, "url": "https://example.test/trigger"},
            ),
            [{"id": 1, "html_url": "https://example.test/1"}],
        )

    def test_format_issue_comments_uses_stable_text_shape(self) -> None:
        self.assertEqual(
            context_snapshot.format_issue_comments(
                [
                    {
                        "user": {"login": "octo"},
                        "created_at": "2026-06-08T00:00:00Z",
                        "body": "hello",
                    }
                ]
            ),
            "Author: octo\nCreated: 2026-06-08T00:00:00Z\n\nhello\n\n---\n",
        )


if __name__ == "__main__":
    unittest.main()
