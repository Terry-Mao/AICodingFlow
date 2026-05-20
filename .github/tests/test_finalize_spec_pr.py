from __future__ import annotations

import unittest
from unittest import mock

from script_imports import import_script


finalize_spec = import_script(".github/scripts/finalize_spec_pr.py", "finalize_spec_pr")


class FinalizeSpecPrTest(unittest.TestCase):
    def test_commit_and_push_specs_recreates_branch_from_default_and_stages_only_specs(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_: object) -> str:
            calls.append(args)
            if args == ["git", "diff", "--cached", "--name-only"]:
                return "specs/issue-77/product.md\nspecs/issue-77/tech.md"
            if args == ["git", "rev-parse", "HEAD"]:
                return "abc123"
            return ""

        context = {
            "default_branch": "main",
            "product_spec": "specs/issue-77/product.md",
            "tech_spec": "specs/issue-77/tech.md",
        }
        metadata = {
            "branch_name": "spec/issue-77",
            "pr_title": "docs(spec): create issue 77 specs",
        }

        with mock.patch.object(finalize_spec, "run", side_effect=fake_run):
            sha = finalize_spec.commit_and_push_specs(
                context,
                metadata,
                "github-actions[bot]",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )

        self.assertEqual(sha, "abc123")
        self.assertIn(["git", "fetch", "origin", "+refs/heads/spec/issue-77:refs/remotes/origin/spec/issue-77"], calls)
        self.assertIn(["git", "switch", "-C", "spec/issue-77", "origin/main"], calls)
        self.assertIn(["git", "add", "specs/issue-77/product.md", "specs/issue-77/tech.md"], calls)
        self.assertIn(["git", "push", "--force-with-lease", "origin", "spec/issue-77"], calls)

    def test_commit_and_push_specs_returns_empty_sha_when_no_staged_diff(self) -> None:
        with mock.patch.object(finalize_spec, "run", return_value=""):
            sha = finalize_spec.commit_and_push_specs(
                {
                    "default_branch": "main",
                    "product_spec": "specs/issue-77/product.md",
                    "tech_spec": "specs/issue-77/tech.md",
                },
                {
                    "branch_name": "spec/issue-77",
                    "pr_title": "docs(spec): create issue 77 specs",
                },
                "github-actions[bot]",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )

        self.assertEqual(sha, "")

    def test_create_or_update_pr_edits_existing_pr(self) -> None:
        context = {"default_branch": "main"}
        metadata = {
            "branch_name": "spec/issue-77",
            "pr_title": "docs(spec): create issue 77 specs",
            "pr_summary": "Refs #77",
        }

        with (
            mock.patch.object(finalize_spec, "open_pr_for_branch", return_value={"number": 82}),
            mock.patch.object(finalize_spec, "edit_pr", return_value="https://github.test/pr/82") as edit_pr,
        ):
            pr_url = finalize_spec.create_or_update_pr("owner/repo", context, metadata)

        self.assertEqual(pr_url, "https://github.test/pr/82")
        edit_pr.assert_called_once_with(
            "owner/repo",
            82,
            "docs(spec): create issue 77 specs",
            "Refs #77",
        )

    def test_create_or_update_pr_creates_pr_when_branch_has_no_open_pr(self) -> None:
        context = {"default_branch": "main"}
        metadata = {
            "branch_name": "spec/issue-77",
            "pr_title": "docs(spec): create issue 77 specs",
            "pr_summary": "Refs #77",
        }

        with (
            mock.patch.object(finalize_spec, "open_pr_for_branch", return_value=None),
            mock.patch.object(finalize_spec, "create_pr", return_value="https://github.test/pr/82") as create_pr,
        ):
            pr_url = finalize_spec.create_or_update_pr("owner/repo", context, metadata)

        self.assertEqual(pr_url, "https://github.test/pr/82")
        create_pr.assert_called_once_with(
            "owner/repo",
            "main",
            "spec/issue-77",
            "docs(spec): create issue 77 specs",
            "Refs #77",
        )


if __name__ == "__main__":
    unittest.main()
