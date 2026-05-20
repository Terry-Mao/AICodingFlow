from __future__ import annotations

import unittest
from subprocess import CompletedProcess
from unittest import mock

from script_imports import import_script


apply_triage = import_script(
    ".github/scripts/apply_issue_triage_result.py",
    "apply_issue_triage_result",
)


class ApplyIssueTriageResultTest(unittest.TestCase):
    def test_build_comment_body_includes_marker_and_issue_body(self) -> None:
        body = apply_triage.build_comment_body(
            {"issue_number": 19},
            {"issue_body": "### Triage\n\nLooks duplicate.", "summary": "fallback"},
        )

        self.assertTrue(body.startswith(apply_triage.MARKER))
        self.assertIn("### Triage\n\nLooks duplicate.", body)

    def test_build_comment_body_falls_back_to_summary(self) -> None:
        body = apply_triage.build_comment_body({"issue_number": 19}, {"issue_body": "", "summary": "Needs info."})

        self.assertIn("### Triage summary", body)
        self.assertIn("Needs info.", body)

    def test_sync_labels_adds_desired_labels_and_removes_stale_managed_labels(self) -> None:
        calls: list[list[str]] = []

        def record(args: list[str], **kwargs) -> CompletedProcess:
            calls.append(args)
            return CompletedProcess(args=args, returncode=0)

        with mock.patch.object(apply_triage.subprocess, "run", side_effect=record):
            apply_triage.sync_labels(
                "owner/repo",
                19,
                {"enhancement", "needs-info", "repro:unknown", "area:workflow", "ready-to-spec"},
                ["documentation", "triaged", "repro:medium"],
                {"documentation", "enhancement", "needs-info", "repro:medium", "repro:unknown", "triaged"},
            )

        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "documentation"], calls)
        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "repro:medium"], calls)
        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "triaged"], calls)
        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--remove-label", "enhancement"], calls)
        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--remove-label", "needs-info"], calls)
        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--remove-label", "repro:unknown"], calls)
        self.assertNotIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--remove-label", "area:workflow"], calls)
        self.assertNotIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--remove-label", "ready-to-spec"], calls)

    def test_sync_labels_never_adds_protected_labels(self) -> None:
        calls: list[list[str]] = []

        def record(args: list[str], **kwargs) -> CompletedProcess:
            calls.append(args)
            return CompletedProcess(args=args, returncode=0)

        with mock.patch.object(apply_triage.subprocess, "run", side_effect=record):
            apply_triage.sync_labels(
                "owner/repo",
                19,
                set(),
                ["plan-approved", "ready-to-implement", "ready-to-spec", "triaged"],
                {"plan-approved", "ready-to-implement", "ready-to-spec", "triaged"},
            )

        self.assertIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "triaged"], calls)
        self.assertNotIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "plan-approved"], calls)
        self.assertNotIn(
            ["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "ready-to-implement"],
            calls,
        )
        self.assertNotIn(["gh", "issue", "edit", "19", "--repo", "owner/repo", "--add-label", "ready-to-spec"], calls)

    def test_configured_label_names_reads_triage_config(self) -> None:
        self.assertEqual(
            apply_triage.configured_label_names(
                {"triage_config": {"labels": {"bug": {}, "documentation": {}, "ready-to-spec": {}}}}
            ),
            {"bug", "documentation", "ready-to-spec"},
        )

    def test_upsert_triage_comment_patches_existing_marker_comment(self) -> None:
        with (
            mock.patch.object(apply_triage, "find_triage_comment", return_value={"id": 123}),
            mock.patch.object(
                apply_triage.subprocess,
                "run",
                return_value=CompletedProcess(args=[], returncode=0),
            ) as run,
        ):
            apply_triage.upsert_triage_comment("owner/repo", 19, "body")

        run.assert_called_once_with(
            ["gh", "api", "repos/owner/repo/issues/comments/123", "-X", "PATCH", "-f", "body=body"],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
