from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


handle_plan_approved = import_script(
    ".github/scripts/handle_plan_approved.py",
    "handle_plan_approved",
)


def pr(
    *,
    body: str = "Refs #57",
    title: str = "docs(spec): create issue 57 specs",
    head_ref: str = "spec/issue-57",
    labels: list[str] | None = None,
) -> dict:
    return {
        "number": 66,
        "title": title,
        "body": body,
        "labels": [{"name": label} for label in (labels or ["plan-approved"])],
        "head": {"ref": head_ref, "repo": {"full_name": "owner/repo"}},
    }


def issue(*, labels: list[str], assignees: list[str] | None = None) -> dict:
    return {
        "number": 57,
        "labels": [{"name": label} for label in labels],
        "assignees": [{"login": login} for login in (assignees or [])],
    }


class HandlePlanApprovedTest(unittest.TestCase):
    def args_for_event(self, event: dict, *, agent_login: str = "codex") -> argparse.Namespace:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        event_path = Path(directory.name) / "event.json"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        return argparse.Namespace(
            repo="owner/repo",
            event_name="pull_request",
            event_path=str(event_path),
            pr_number="66",
            agent_login=agent_login,
            github_output="",
            dry_run=False,
        )

    def test_resolves_linked_issue_from_pr_body_before_branch(self) -> None:
        self.assertEqual(
            handle_plan_approved.resolve_linked_issue_number(
                pr(body="Closes #57", title="spec for 99", head_ref="spec/issue-42")
            ),
            57,
        )

    def test_resolves_linked_issue_from_spec_branch_fallback(self) -> None:
        self.assertEqual(
            handle_plan_approved.resolve_linked_issue_number(pr(body="", title="spec update", head_ref="spec/issue-57")),
            57,
        )

    def test_bare_hash_and_gh_refs_do_not_override_spec_branch_fallback(self) -> None:
        self.assertEqual(
            handle_plan_approved.resolve_linked_issue_number(
                pr(body="See #99 for background", title="GH-88", head_ref="spec/issue-57")
            ),
            57,
        )

    def test_does_not_resolve_unqualified_numbers(self) -> None:
        self.assertIsNone(
            handle_plan_approved.resolve_linked_issue_number(
                pr(body="updated 57 files", title="spec 57", head_ref="feature/issue-57")
            )
        )

    def test_skips_when_linked_issue_is_missing(self) -> None:
        args = self.args_for_event({"pull_request": pr(body="", title="spec update", head_ref="feature/no-issue")})

        outputs = handle_plan_approved.handle_plan_approved(args)

        self.assertEqual(outputs["skip_reason"], "linked issue not found")
        self.assertEqual(outputs["implementation_dispatched"], "false")

    def test_skips_non_spec_pr_without_modifying_issue(self) -> None:
        args = self.args_for_event({"pull_request": pr(body="Refs #57", head_ref="feature/issue-57")})

        with mock.patch.object(handle_plan_approved, "fetch_issue") as fetch_issue:
            outputs = handle_plan_approved.handle_plan_approved(args)

        self.assertEqual(outputs["issue_number"], "57")
        self.assertEqual(outputs["skip_reason"], "pull request is not a spec PR")
        fetch_issue.assert_not_called()

    def test_removes_ready_to_spec_and_dispatches_when_issue_is_ready_and_assigned(self) -> None:
        args = self.args_for_event(
            {
                "pull_request": pr(),
                "repository": {"default_branch": "main"},
            }
        )

        with (
            mock.patch.object(
                handle_plan_approved,
                "fetch_issue",
                return_value=issue(labels=["ready-to-spec", "ready-to-implement"], assignees=["codex"]),
            ),
            mock.patch.object(handle_plan_approved, "remove_ready_to_spec_label", return_value=True) as remove_label,
            mock.patch.object(handle_plan_approved, "dispatch_implementation") as dispatch,
        ):
            outputs = handle_plan_approved.handle_plan_approved(args)

        remove_label.assert_called_once_with("owner/repo", 57, False)
        dispatch.assert_called_once_with("owner/repo", "main", 57, "codex", False)
        self.assertEqual(outputs["removed_ready_to_spec"], "true")
        self.assertEqual(outputs["has_ready_to_implement"], "true")
        self.assertEqual(outputs["has_agent_assignee"], "true")
        self.assertEqual(outputs["implementation_dispatched"], "true")
        self.assertEqual(outputs["skip_reason"], "")

    def test_missing_ready_to_implement_only_syncs_ready_to_spec(self) -> None:
        args = self.args_for_event({"pull_request": pr(), "repository": {"default_branch": "main"}})

        with (
            mock.patch.object(
                handle_plan_approved,
                "fetch_issue",
                return_value=issue(labels=["ready-to-spec"], assignees=["codex"]),
            ),
            mock.patch.object(handle_plan_approved, "remove_ready_to_spec_label", return_value=True),
            mock.patch.object(handle_plan_approved, "dispatch_implementation") as dispatch,
        ):
            outputs = handle_plan_approved.handle_plan_approved(args)

        dispatch.assert_not_called()
        self.assertEqual(outputs["removed_ready_to_spec"], "true")
        self.assertEqual(outputs["implementation_dispatched"], "false")
        self.assertEqual(outputs["skip_reason"], "missing ready-to-implement")

    def test_missing_bot_assignee_does_not_dispatch(self) -> None:
        args = self.args_for_event({"pull_request": pr(), "repository": {"default_branch": "main"}})

        with (
            mock.patch.object(
                handle_plan_approved,
                "fetch_issue",
                return_value=issue(labels=["ready-to-spec", "ready-to-implement"], assignees=[]),
            ),
            mock.patch.object(handle_plan_approved, "remove_ready_to_spec_label", return_value=True),
            mock.patch.object(handle_plan_approved, "dispatch_implementation") as dispatch,
        ):
            outputs = handle_plan_approved.handle_plan_approved(args)

        dispatch.assert_not_called()
        self.assertEqual(outputs["has_ready_to_implement"], "true")
        self.assertEqual(outputs["has_agent_assignee"], "false")
        self.assertEqual(outputs["skip_reason"], "missing bot assignee")

    def test_missing_agent_login_does_not_dispatch(self) -> None:
        args = self.args_for_event({"pull_request": pr(), "repository": {"default_branch": "main"}}, agent_login="")

        with (
            mock.patch.object(
                handle_plan_approved,
                "fetch_issue",
                return_value=issue(labels=["ready-to-implement"], assignees=["codex"]),
            ),
            mock.patch.object(handle_plan_approved, "remove_ready_to_spec_label") as remove_label,
            mock.patch.object(handle_plan_approved, "dispatch_implementation") as dispatch,
        ):
            outputs = handle_plan_approved.handle_plan_approved(args)

        remove_label.assert_not_called()
        dispatch.assert_not_called()
        self.assertEqual(outputs["skip_reason"], "missing agent login")

    def test_missing_ready_to_spec_is_idempotent(self) -> None:
        args = self.args_for_event({"pull_request": pr(), "repository": {"default_branch": "main"}})

        with (
            mock.patch.object(
                handle_plan_approved,
                "fetch_issue",
                return_value=issue(labels=["ready-to-implement"], assignees=["codex"]),
            ),
            mock.patch.object(handle_plan_approved, "remove_ready_to_spec_label") as remove_label,
            mock.patch.object(handle_plan_approved, "dispatch_implementation"),
        ):
            outputs = handle_plan_approved.handle_plan_approved(args)

        remove_label.assert_not_called()
        self.assertEqual(outputs["removed_ready_to_spec"], "false")
        self.assertEqual(outputs["implementation_dispatched"], "true")

    def test_remove_ready_to_spec_label_treats_404_as_idempotent(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"],
            returncode=1,
            stdout="",
            stderr="gh: Not Found (HTTP 404)",
        )
        with mock.patch.object(handle_plan_approved.subprocess, "run", return_value=completed):
            self.assertFalse(handle_plan_approved.remove_ready_to_spec_label("owner/repo", 57))

    def test_remove_ready_to_spec_label_raises_other_api_errors(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["gh"],
            returncode=1,
            stdout="",
            stderr="gh: Forbidden (HTTP 403)",
        )
        with mock.patch.object(handle_plan_approved.subprocess, "run", return_value=completed):
            with self.assertRaises(subprocess.CalledProcessError):
                handle_plan_approved.remove_ready_to_spec_label("owner/repo", 57)


if __name__ == "__main__":
    unittest.main()
