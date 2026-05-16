from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from tests.script_imports import import_script


prepare_local = import_script(".github/scripts/prepare_local_review_inputs.py", "prepare_local_review_inputs")


CODE_DIFF = [
    "diff --git a/core/foo.py b/core/foo.py",
    "index 1111111..2222222 100644",
    "--- a/core/foo.py",
    "+++ b/core/foo.py",
    "@@ -1 +1 @@",
    "-old",
    "+new",
]

SPEC_DIFF = [
    "diff --git a/specs/issue-80/product.md b/specs/issue-80/product.md",
    "index 1111111..2222222 100644",
    "--- a/specs/issue-80/product.md",
    "+++ b/specs/issue-80/product.md",
    "@@ -1 +1 @@",
    "-old",
    "+new",
]


class PrepareLocalReviewInputsTest(unittest.TestCase):
    def run_in_tempdir(self, callback) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                callback(Path(directory))
            finally:
                os.chdir(old_cwd)

    def common_patches(self, diff_lines: list[str]):
        return (
            mock.patch.object(prepare_local, "require_clean_worktree"),
            mock.patch.object(prepare_local, "default_repo", return_value="owner/repo"),
            mock.patch.object(prepare_local, "default_base", return_value="upstream/main"),
            mock.patch.object(prepare_local, "resolve_ref", side_effect=["base-sha", "head-sha"]),
            mock.patch.object(
                prepare_local,
                "local_pr_event",
                return_value={
                    "pull_request": {
                        "number": "",
                        "title": "feat: local review",
                        "body": "",
                        "html_url": "",
                        "user": {"login": "dev"},
                        "base": {"ref": "main", "sha": "base-sha", "repo": {"default_branch": "main"}},
                        "head": {"ref": "feat/local-review-skills-80", "sha": "head-sha"},
                    }
                },
            ),
            mock.patch.object(prepare_local.build_pr_diff, "run_git_diff", return_value=diff_lines),
        )

    def test_prepares_code_review_inputs_and_removes_stale_files(self) -> None:
        def scenario(directory: Path) -> None:
            for name in ("pr_description.txt", "pr_diff.txt", "spec_context.md", "review.json"):
                Path(name).write_text("stale", encoding="utf-8")

            with ExitStack() as stack:
                for patcher in self.common_patches(CODE_DIFF):
                    stack.enter_context(patcher)
                resolve_spec_context = stack.enter_context(
                    mock.patch.object(
                        prepare_local.write_spec_context,
                        "resolve_spec_context",
                        return_value={"spec_context_source": "", "spec_entries": []},
                    )
                )
                stack.enter_context(mock.patch("sys.argv", ["prepare_local_review_inputs.py"]))
                self.assertEqual(prepare_local.main(), 0)

            self.assertIn("Title: feat: local review", Path("pr_description.txt").read_text(encoding="utf-8"))
            self.assertIn("FILE core/foo.py", Path("pr_diff.txt").read_text(encoding="utf-8"))
            self.assertFalse(Path("spec_context.md").exists())
            self.assertFalse(Path("review.json").exists())
            resolve_spec_context.assert_called_once()

        self.run_in_tempdir(scenario)

    def test_prepares_spec_review_inputs_without_spec_context(self) -> None:
        def scenario(directory: Path) -> None:
            Path("spec_context.md").write_text("stale", encoding="utf-8")

            with ExitStack() as stack:
                for patcher in self.common_patches(SPEC_DIFF):
                    stack.enter_context(patcher)
                resolve_spec_context = stack.enter_context(
                    mock.patch.object(prepare_local.write_spec_context, "resolve_spec_context")
                )
                stack.enter_context(
                    mock.patch(
                        "sys.argv",
                        [
                            "prepare_local_review_inputs.py",
                            "--expected-skill",
                            ".agents/skills/review-spec-repo/SKILL.md",
                        ],
                    )
                )
                self.assertEqual(prepare_local.main(), 0)

            self.assertIn("FILE specs/issue-80/product.md", Path("pr_diff.txt").read_text(encoding="utf-8"))
            self.assertFalse(Path("spec_context.md").exists())
            resolve_spec_context.assert_not_called()

        self.run_in_tempdir(scenario)

    def test_rejects_unexpected_selected_skill(self) -> None:
        def scenario(directory: Path) -> None:
            with ExitStack() as stack:
                for patcher in self.common_patches(SPEC_DIFF):
                    stack.enter_context(patcher)
                stack.enter_context(
                    mock.patch(
                        "sys.argv",
                        [
                            "prepare_local_review_inputs.py",
                            "--expected-skill",
                            ".agents/skills/review-pr-repo/SKILL.md",
                        ],
                    )
                )
                with self.assertRaisesRegex(SystemExit, "expected .agents/skills/review-pr-repo/SKILL.md"):
                    prepare_local.main()

        self.run_in_tempdir(scenario)

    def test_gitignore_excludes_root_review_snapshots(self) -> None:
        gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
        for path in ("pr_description.txt", "pr_diff.txt", "spec_context.md", "review.json"):
            self.assertIn(f"/{path}", gitignore)

    def test_remote_repo_from_url_accepts_ssh_https_and_dotted_names(self) -> None:
        self.assertEqual(
            prepare_local.remote_repo_from_url("git@github.com:owner/repo.name.git"),
            "owner/repo.name",
        )
        self.assertEqual(
            prepare_local.remote_repo_from_url("https://github.com/owner/repo.name.git"),
            "owner/repo.name",
        )


if __name__ == "__main__":
    unittest.main()
