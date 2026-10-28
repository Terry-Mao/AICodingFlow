from __future__ import annotations

import unittest
from unittest import mock

from script_imports import import_script


dispatch_pr_review = import_script(".github/scripts/dispatch_pr_review.py", "dispatch_pr_review")


def pr(*, number: int = 42, draft: bool = False, state: str = "open", head_repo: str = "owner/repo") -> dict:
    return {
        "number": number,
        "draft": draft,
        "state": state,
        "head": {"repo": {"full_name": head_repo}},
    }


class DispatchPrReviewTest(unittest.TestCase):
    def test_dispatches_open_non_draft_pr_by_url(self) -> None:
        with (
            mock.patch.object(dispatch_pr_review, "run_gh_json", return_value=pr()) as api,
            mock.patch.object(dispatch_pr_review.subprocess, "run") as run,
        ):
            dispatched = dispatch_pr_review.dispatch("owner/repo", pr_url="https://github.com/owner/repo/pull/42")

        self.assertTrue(dispatched)
        api.assert_called_once_with(["api", "repos/owner/repo/pulls/42"])
        run.assert_called_once_with(
            ["gh", "workflow", "run", "review-pr.yml", "--repo", "owner/repo", "-f", "pr_number=42"],
            check=True,
        )

    def test_skips_draft_pr_found_by_branch(self) -> None:
        with (
            mock.patch.object(dispatch_pr_review, "run_gh_json", return_value=[pr(draft=True)]) as api,
            mock.patch.object(dispatch_pr_review.subprocess, "run") as run,
        ):
            dispatched = dispatch_pr_review.dispatch("owner/repo", head_branch="docs/update")

        self.assertFalse(dispatched)
        api.assert_called_once_with(["api", "repos/owner/repo/pulls?state=open&head=owner%3Adocs%2Fupdate&per_page=100"])
        run.assert_not_called()

    def test_rejects_fork_pr_and_foreign_url(self) -> None:
        with mock.patch.object(dispatch_pr_review, "run_gh_json", return_value=pr(head_repo="other/repo")):
            with self.assertRaisesRegex(SystemExit, "fork PR"):
                dispatch_pr_review.dispatch("owner/repo", pr_url="https://github.com/owner/repo/pull/42")
        with self.assertRaisesRegex(SystemExit, "does not belong"):
            dispatch_pr_review.dispatch("owner/repo", pr_url="https://github.com/other/repo/pull/42")


if __name__ == "__main__":
    unittest.main()
