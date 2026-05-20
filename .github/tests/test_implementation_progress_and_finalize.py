from __future__ import annotations

import unittest
from subprocess import CompletedProcess
from unittest import mock

from script_imports import import_script


progress = import_script(
    ".github/scripts/update_implementation_progress.py",
    "update_implementation_progress",
)
finalize = import_script(
    ".github/scripts/finalize_implementation_pr.py",
    "finalize_implementation_pr",
)


class ImplementationProgressAndFinalizeTest(unittest.TestCase):
    def test_progress_body_includes_marker_status_message_and_pr_url(self) -> None:
        body = progress.build_body(
            {"issue_number": 18},
            "ready for review",
            "Review the implementation changes.",
            "https://github.test/owner/repo/pull/123",
        )

        self.assertIn(progress.MARKER, body)
        self.assertIn("Implementation status for issue #18: **ready for review**.", body)
        self.assertIn("Review the implementation changes.", body)
        self.assertIn("Pull request: https://github.test/owner/repo/pull/123", body)

    def test_progress_body_can_report_validation_failure(self) -> None:
        body = progress.build_body(
            {"issue_number": 18},
            "failed",
            "pr-metadata.json was not created",
        )

        self.assertIn("Implementation status for issue #18: **failed**.", body)
        self.assertIn("pr-metadata.json was not created", body)

    def test_finalize_edits_selected_spec_pr_for_approved_context(self) -> None:
        context = {
            "spec_context_source": "approved-pr",
            "selected_spec_pr_number": 123,
            "default_branch": "main",
        }
        metadata = {
            "branch_name": "spec/issue-18",
            "pr_title": "feat: implement issue",
            "pr_summary": "Closes #18\n\n## Summary\n- Done",
        }

        with mock.patch.object(finalize, "edit_pr", return_value="https://github.test/pr/123") as edit_pr:
            pr_url = finalize.finalize("owner/repo", context, metadata)

        self.assertEqual(pr_url, "https://github.test/pr/123")
        edit_pr.assert_called_once_with(
            "owner/repo",
            "123",
            "feat: implement issue",
            "Closes #18\n\n## Summary\n- Done",
        )

    def test_finalize_creates_draft_pr_when_branch_has_no_open_pr(self) -> None:
        context = {
            "spec_context_source": "directory",
            "default_branch": "main",
        }
        metadata = {
            "branch_name": "spec/implement-issue-18",
            "pr_title": "feat: implement issue",
            "pr_summary": "Closes #18\n\n## Summary\n- Done",
        }

        with (
            mock.patch.object(finalize, "open_pr_for_branch", return_value=None),
            mock.patch.object(
                finalize,
                "create_pr",
                return_value="https://github.test/pr/124",
            ) as create_pr,
        ):
            pr_url = finalize.finalize("owner/repo", context, metadata)

        self.assertEqual(pr_url, "https://github.test/pr/124")
        create_pr.assert_called_once_with(
            "owner/repo",
            "main",
            "spec/implement-issue-18",
            "feat: implement issue",
            "Closes #18\n\n## Summary\n- Done",
        )

    def test_create_pr_creates_draft_pr(self) -> None:
        with mock.patch.object(
            finalize.subprocess,
            "run",
            return_value=CompletedProcess(args=[], returncode=0, stdout="https://github.test/owner/repo/pull/124\n"),
        ) as run:
            pr_url = finalize.create_pr("owner/repo", "main", "feature-branch", "feat: title", "Body")

        args = run.call_args.args[0]
        self.assertEqual(pr_url, "https://github.test/owner/repo/pull/124")
        self.assertIn("create", args)
        self.assertIn("--draft", args)


if __name__ == "__main__":
    unittest.main()
