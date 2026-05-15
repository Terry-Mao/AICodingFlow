from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.script_imports import import_script


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
    def test_pull_request_event_reuses_existing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event = {"pull_request": pr_payload(number=11)}
            event_path.write_text(json.dumps(event), encoding="utf-8")

            self.assertEqual(
                resolver.resolve_event("owner/repo", "pull_request", event_path, ""),
                event,
            )

    def test_pull_request_target_event_reuses_existing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event = {"pull_request": pr_payload(number=11, head_repo="fork/repo")}
            event_path.write_text(json.dumps(event), encoding="utf-8")

            self.assertEqual(
                resolver.resolve_event("owner/repo", "pull_request_target", event_path, ""),
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
                json.dumps({"issue": {"number": 22, "pull_request": {"url": "https://github.test/pr/22"}}}),
                encoding="utf-8",
            )
            with mock.patch.object(resolver, "fetch_pr", return_value=fetched) as fetch_pr:
                self.assertEqual(
                    resolver.resolve_event("owner/repo", "issue_comment", event_path, ""),
                    {"pull_request": fetched},
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

    def test_review_state_allows_manual_comment_review_for_draft_same_repo_pr(self) -> None:
        self.assertEqual(
            resolver.review_state(
                {"pull_request": pr_payload(draft=True)},
                "owner/repo",
                "issue_comment",
            )["reviewable"],
            "true",
        )
        self.assertEqual(
            resolver.review_state(
                {"pull_request": pr_payload(draft=True, head_repo="fork/repo")},
                "owner/repo",
                "issue_comment",
            )["reviewable"],
            "true",
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
