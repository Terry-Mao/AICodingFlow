from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


resolver = import_script(".github/scripts/resolve_pr_event.py", "resolve_pr_event")


def pr_payload(*, number: int = 7, draft: bool = False, head_repo: str = "owner/repo", state: str = "open") -> dict:
    return {
        "number": number,
        "state": state,
        "draft": draft,
        "base": {"sha": "base123", "ref": "main"},
        "head": {"sha": "head456", "ref": "feature", "repo": {"full_name": head_repo}},
    }


class ResolvePrEventTest(unittest.TestCase):
    def test_comment_has_review_command_accepts_body_level_bot_command(self) -> None:
        self.assertTrue(resolver.comment_has_review_command("@codex /review", "codex"))
        self.assertTrue(resolver.comment_has_review_command("\n  @codex /review  \n", "codex"))
        self.assertTrue(resolver.comment_has_review_command("hello\n@codex /review\nthanks", "codex"))

    def test_comment_has_review_command_rejects_non_commands(self) -> None:
        invalid_bodies = [
            "",
            "/review",
            "@codex",
            "please @codex /review this",
            "@codex /review now",
            "> @codex /review",
            "```\n@codex /review\n```",
            "```text\n@codex /review\n```\n@codex",
        ]

        for body in invalid_bodies:
            with self.subTest(body=body):
                self.assertFalse(resolver.comment_has_review_command(body, "codex"))

        self.assertFalse(resolver.comment_has_review_command("@codex /review", ""))
        self.assertFalse(resolver.comment_has_review_command(None, "codex"))

    def test_comment_has_fix_command_allows_trailing_request_text(self) -> None:
        self.assertTrue(resolver.comment_has_fix_command("@codex /fix", "codex"))
        self.assertTrue(resolver.comment_has_fix_command("@codex /fix please address this", "codex"))
        self.assertTrue(resolver.comment_has_fix_command("hello\n@codex /fix this edge case", "codex"))

    def test_comment_has_fix_command_rejects_invisible_or_partial_commands(self) -> None:
        invalid_bodies = [
            "please @codex /fix",
            "@codex /review",
            "@codex-bot /fix",
            "> @codex /fix",
            "```\n@codex /fix\n```",
        ]
        for body in invalid_bodies:
            with self.subTest(body=body):
                self.assertFalse(resolver.comment_has_fix_command(body, "codex"))

    def test_pull_request_event_reuses_existing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event = {"pull_request": pr_payload(number=11)}
            event_path.write_text(json.dumps(event), encoding="utf-8")

            self.assertEqual(
                resolver.resolve_event("owner/repo", "pull_request", event_path, ""),
                event,
            )

    def test_workflow_dispatch_fetches_pr_payload(self) -> None:
        fetched = pr_payload(number=12)
        with mock.patch.object(resolver, "fetch_pr", return_value=fetched) as fetch_pr:
            self.assertEqual(
                resolver.resolve_event("owner/repo", "workflow_dispatch", Path("unused.json"), "12"),
                {"pull_request": fetched},
            )

        fetch_pr.assert_called_once_with("owner/repo", "12")

    def test_issue_comment_event_fetches_linked_pr_payload(self) -> None:
        fetched = pr_payload(number=22)
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "issue": {"number": 22, "pull_request": {"url": "https://github.test/pr/22"}},
                        "comment": {"body": "@codex /review"},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(resolver, "fetch_pr", return_value=fetched) as fetch_pr:
                self.assertEqual(
                    resolver.resolve_event("owner/repo", "issue_comment", event_path, "", "codex"),
                    {"pull_request": fetched, "comment": {"body": "@codex /review"}, "review_command": True},
                )

        fetch_pr.assert_called_once_with("owner/repo", "22")

    def test_issue_comment_event_rejects_regular_issue_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"issue": {"number": 22}}), encoding="utf-8")

            with self.assertRaisesRegex(SystemExit, "not for a pull request"):
                resolver.resolve_event("owner/repo", "issue_comment", event_path, "")

    def test_review_state_marks_same_repo_non_draft_pr_reviewable(self) -> None:
        state = resolver.review_state({"pull_request": pr_payload(number=13)}, "owner/repo")

        self.assertEqual(
            state,
            {
                "number": "13",
                "state": "open",
                "base_sha": "base123",
                "head_sha": "head456",
                "draft": "false",
                "head_repo": "owner/repo",
                "reviewable": "true",
                "skip_reason": "",
            },
        )

    def test_review_state_skips_draft_and_closed_prs(self) -> None:
        self.assertEqual(
            resolver.review_state({"pull_request": pr_payload(draft=True)}, "owner/repo")["reviewable"],
            "false",
        )
        self.assertEqual(
            resolver.review_state({"pull_request": pr_payload(state="closed")}, "owner/repo")["reviewable"],
            "false",
        )

    def test_review_state_allows_open_non_draft_fork_prs(self) -> None:
        self.assertEqual(
            resolver.review_state({"pull_request": pr_payload(head_repo="fork/repo")}, "owner/repo")["reviewable"],
            "true",
        )

    def test_review_state_allows_valid_comment_review_for_open_non_draft_pr(self) -> None:
        self.assertEqual(
            resolver.review_state(
                {"pull_request": pr_payload(draft=False), "review_command": True},
                "owner/repo",
                "issue_comment",
            )["reviewable"],
            "true",
        )

    def test_review_state_skips_issue_comments_without_valid_review_command(self) -> None:
        state = resolver.review_state(
            {"pull_request": pr_payload(draft=False), "review_command": False},
            "owner/repo",
            "issue_comment",
        )

        self.assertEqual(state["reviewable"], "false")
        self.assertEqual(state["skip_reason"], "missing valid @AGENT_LOGIN /review command")

    def test_review_state_skips_manual_comment_review_for_draft_pr(self) -> None:
        self.assertEqual(
            resolver.review_state(
                {"pull_request": pr_payload(draft=True), "review_command": True},
                "owner/repo",
                "issue_comment",
            )["reviewable"],
            "false",
        )
        self.assertEqual(
            resolver.review_state(
                {"pull_request": pr_payload(draft=True, head_repo="fork/repo"), "review_command": True},
                "owner/repo",
                "issue_comment",
            )["reviewable"],
            "false",
        )

    def test_main_writes_event_file_and_github_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            output_path = Path(directory) / "pr_event.json"
            github_output = Path(directory) / "github_output.txt"
            event_path.write_text(json.dumps({"pull_request": pr_payload(number=21)}), encoding="utf-8")

            with mock.patch(
                "sys.argv",
                [
                    "resolve_pr_event.py",
                    "--repo",
                    "owner/repo",
                    "--event-name",
                    "pull_request",
                    "--event-path",
                    str(event_path),
                    "--output",
                    str(output_path),
                    "--github-output",
                    str(github_output),
                ],
            ):
                resolver.main()

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["pull_request"]["number"], 21)
            output = github_output.read_text(encoding="utf-8")
            self.assertIn(f"event_path={output_path.resolve()}\n", output)
            self.assertIn("number=21\n", output)
            self.assertIn("state=open\n", output)
            self.assertIn("base_sha=base123\n", output)
            self.assertIn("head_sha=head456\n", output)
            self.assertIn("reviewable=true\n", output)


if __name__ == "__main__":
    unittest.main()
