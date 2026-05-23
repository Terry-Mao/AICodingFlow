from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from script_imports import import_script


prepare = import_script(
    ".github/scripts/prepare_issue_triage_context.py",
    "prepare_issue_triage_context",
)


class PrepareIssueTriageContextTest(unittest.TestCase):
    def args(self, *, event_name: str, event_path: str = "", agent_login: str = "codex") -> argparse.Namespace:
        return argparse.Namespace(event_name=event_name, event_path=event_path, agent_login=agent_login)

    def test_should_run_for_opened_issue(self) -> None:
        self.assertEqual(
            prepare.should_run(
                self.args(event_name="issues"),
                {"action": "opened", "issue": {"user": {"login": "external", "type": "User"}}},
            ),
            (True, "issue opened"),
        )

    def test_should_run_for_reopened_issue(self) -> None:
        self.assertEqual(
            prepare.should_run(
                self.args(event_name="issues"),
                {"action": "reopened", "issue": {"user": {"login": "external", "type": "User"}}},
            ),
            (True, "issue reopened"),
        )

    def test_should_not_run_for_bot_authored_issue(self) -> None:
        event = {
            "action": "opened",
            "issue": {"user": {"login": "github-actions[bot]", "type": "Bot"}},
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issues"), event),
            (False, "issue author is a bot or automation user"),
        )

    def test_should_not_run_for_pr_issue_event(self) -> None:
        event = {
            "action": "opened",
            "issue": {"number": 1, "pull_request": {}, "user": {"login": "alice", "type": "User"}},
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issues"), event),
            (False, "PR issue events are not issue triage targets"),
        )

    def test_should_not_run_for_untrusted_comment_author(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "@codex /triage please rerun",
                "author_association": "CONTRIBUTOR",
                "user": {"login": "bob", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "comment author association is not trusted: CONTRIBUTOR"),
        )

    def test_should_run_for_trusted_triage_command(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "@codex /triage check whether this is a duplicate of #123",
                "author_association": "MEMBER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (True, "trusted issue comment requested @codex /triage"),
        )

    def test_issue_comment_uses_configured_agent_login_exactly(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "@other-bot /triage",
                "author_association": "MEMBER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment", agent_login="codex"), event),
            (False, "issue comment did not contain @codex /triage command"),
        )

    def test_should_not_run_for_plain_bot_mention_without_triage_command(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "@codex check whether this is a duplicate of #123",
                "author_association": "MEMBER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "issue comment did not contain @codex /triage command"),
        )

    def test_should_not_run_for_quoted_triage_command(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "> @codex /triage old request\nI agree",
                "author_association": "OWNER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "issue comment did not contain @codex /triage command"),
        )

    def test_should_not_run_for_triage_command_inside_fenced_code(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "user": {"login": "alice", "type": "User"}},
            "comment": {
                "body": "```\n@codex /triage\n```",
                "author_association": "OWNER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "issue comment did not contain @codex /triage command"),
        )

    def test_should_not_run_for_pull_request_comment(self) -> None:
        event = {
            "action": "created",
            "issue": {"number": 1, "pull_request": {}},
            "comment": {
                "body": "@codex /triage",
                "author_association": "OWNER",
                "user": {"login": "maintainer", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "PR issue events are not issue triage targets"),
        )

    def test_should_run_when_needs_info_issue_author_replies_without_command(self) -> None:
        event = {
            "action": "created",
            "issue": {
                "number": 1,
                "labels": [{"name": "needs-info"}],
                "user": {"login": "alice", "type": "User"},
            },
            "comment": {
                "body": "Here is the missing detail.",
                "author_association": "CONTRIBUTOR",
                "user": {"login": "alice", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment", agent_login=""), event),
            (True, "needs-info issue author replied"),
        )

    def test_should_not_run_when_non_author_replies_to_needs_info_without_command(self) -> None:
        event = {
            "action": "created",
            "issue": {
                "number": 1,
                "labels": [{"name": "needs-info"}],
                "user": {"login": "alice", "type": "User"},
            },
            "comment": {
                "body": "I have the same problem.",
                "author_association": "CONTRIBUTOR",
                "user": {"login": "bob", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "comment author association is not trusted: CONTRIBUTOR"),
        )

    def test_should_not_run_for_bot_comment(self) -> None:
        event = {
            "action": "created",
            "issue": {
                "number": 1,
                "labels": [{"name": "needs-info"}],
                "user": {"login": "alice", "type": "User"},
            },
            "comment": {
                "body": "Automated update",
                "author_association": "NONE",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "comment author is a bot or automation user"),
        )

    def test_should_not_run_for_edited_comment(self) -> None:
        event = {
            "action": "edited",
            "issue": {
                "number": 1,
                "labels": [{"name": "needs-info"}],
                "user": {"login": "alice", "type": "User"},
            },
            "comment": {
                "body": "Here is the missing detail.",
                "author_association": "CONTRIBUTOR",
                "user": {"login": "alice", "type": "User"},
            },
        }

        self.assertEqual(
            prepare.should_run(self.args(event_name="issue_comment"), event),
            (False, "issue comment action is not a triage trigger: edited"),
        )

    def test_triggering_comment_extracts_stable_fields(self) -> None:
        event = {
            "comment": {
                "id": 123,
                "body": "@codex /triage again",
                "author_association": "OWNER",
                "created_at": "2026-05-19T00:00:00Z",
                "html_url": "https://github.test/comment",
                "user": {"login": "maintainer"},
            }
        }

        self.assertEqual(
            prepare.triggering_comment(event),
            {
                "id": 123,
                "author": "maintainer",
                "author_association": "OWNER",
                "body": "@codex /triage again",
                "created_at": "2026-05-19T00:00:00Z",
                "url": "https://github.test/comment",
            },
        )

    def test_read_issue_templates_returns_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / ".github" / "ISSUE_TEMPLATE" / "bug.md"
            template.parent.mkdir(parents=True)
            template.write_text("bug template", encoding="utf-8")

            self.assertEqual(
                prepare.read_issue_templates(root),
                [{"path": ".github/ISSUE_TEMPLATE/bug.md", "body": "bug template"}],
            )

    def test_load_event_extract_issue_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"issue": {"number": 42}}), encoding="utf-8")
            event = prepare.load_event(str(event_path))

        self.assertEqual(prepare.extract_issue_number("", event), 42)

    def test_dedupe_candidates_fetches_open_and_recent_closed_issues(self) -> None:
        open_issues = [
            {"number": 1, "title": "current", "body": "current"},
            {"number": 2, "title": "same", "body": "same failure", "state": "open", "user": {"login": "alice"}},
            {"number": 3, "title": "pr", "pull_request": {}, "state": "open"},
        ]
        closed_issues = [
            {
                "number": 4,
                "title": "recent",
                "body": "same error",
                "state": "closed",
                "closed_at": "2026-05-18T00:00:00Z",
                "labels": [{"name": "bug"}],
            },
            {
                "number": 5,
                "title": "old but updated",
                "body": "same error",
                "state": "closed",
                "closed_at": "2026-05-01T00:00:00Z",
            },
            {"number": 2, "title": "duplicate fetch", "state": "closed"},
        ]

        with mock.patch.object(prepare, "fetch_issue_candidates", side_effect=[open_issues, closed_issues]) as fetch:
            candidates = prepare.dedupe_candidates(
                "owner/repo",
                1,
                now=datetime(2026, 5, 19, tzinfo=timezone.utc),
            )

        self.assertEqual(fetch.call_args_list[0].args, ("owner/repo", "open"))
        self.assertEqual(fetch.call_args_list[1].args, ("owner/repo", "closed"))
        self.assertEqual(fetch.call_args_list[1].kwargs, {"since": "2026-05-12T00:00:00Z"})
        self.assertEqual([candidate["number"] for candidate in candidates], [2, 4])
        self.assertEqual(candidates[0]["author"], "alice")
        self.assertEqual(candidates[1]["labels"], ["bug"])

    def test_write_dedupe_candidates_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dedupe_candidates.json"
            prepare.write_dedupe_candidates(path, [{"number": 2, "title": "same"}])

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [{"number": 2, "title": "same"}])


if __name__ == "__main__":
    unittest.main()
